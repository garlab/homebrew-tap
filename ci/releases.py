"""Verify upstream releases and allow only generated formula updates to publish.

No PR Ruby, scripts or workflow files are executed by this module. GitHub API
writes happen only in `open_pr`, after verification, with a short-lived App token.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

UPSTREAM = 'garlab/probl'
TAP = 'garlab/homebrew-tap'
FORMULA = 'Formula/probl.rb'
METADATA = 'releases/probl.json'
TAG = r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def api(path, data=None, method=None, missing=False):
    request = urllib.request.Request(
        'https://api.github.com/' + path,
        data=None if data is None else json.dumps(data).encode(),
        method=method,
        headers={'Authorization': f"Bearer {os.environ['GH_TOKEN']}",
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        if missing and error.code == 404:
            return None
        raise


def version(tag):
    require(isinstance(tag, str) and re.fullmatch(TAG, tag), 'Invalid stable release tag')
    return tuple(map(int, tag[1:].split('.')))


def validate_manifest(manifest, tag, commit):
    version(tag)
    require(set(manifest) == {'schema', 'tag', 'commit', 'archive', 'sha256'}, 'Unknown manifest schema')
    require(manifest['schema'] == 1 and manifest['tag'] == tag, 'Release identity mismatch')
    require(re.fullmatch(r'[0-9a-f]{40}', commit) and manifest['commit'] == commit, 'Release commit mismatch')
    require(manifest['archive'] == f'probl-{tag[1:]}-source.tar.gz', 'Unexpected archive name')
    require(re.fullmatch(r'[0-9a-f]{64}', manifest['sha256']), 'Invalid checksum')


def contents(path, ref, missing=False):
    result = api(f'repos/{TAP}/contents/{path}?ref={ref}', missing=missing)
    if result is None:
        return None
    require(result['type'] == 'file' and result['encoding'] == 'base64', 'Expected a plain file')
    return base64.b64decode(result['content']).decode()


def formula_version(source):
    match = re.search(r'/v([0-9]+\.[0-9]+\.[0-9]+)(?:/|\.tar)', source)
    require(match is not None, 'Cannot find current formula version')
    return version('v' + match[1])


def render(source, manifest):
    tag = manifest['tag']
    url = f'https://github.com/{UPSTREAM}/releases/download/{tag}/{manifest["archive"]}'
    # Only this generated block is discarded; everything else stays byte-for-byte.
    source = re.sub(r'\n  bottle do\n.*?\n  end\n', '', source, flags=re.S)
    source, urls = re.subn(r'^  url "[^"\n]+"$', f'  url "{url}"', source, flags=re.M)
    source, hashes = re.subn(r'^  sha256 "[0-9a-f]{64}"$', f'  sha256 "{manifest["sha256"]}"', source, flags=re.M)
    require(urls == hashes == 1, 'Expected exactly one source URL and checksum')
    return source


def verified_release(tag):
    version(tag)
    release = api(f'repos/{UPSTREAM}/releases/tags/{tag}')
    require(not release['draft'] and not release['prerelease'] and release.get('immutable'),
            'Only published immutable stable releases are accepted')
    obj = api(f'repos/{UPSTREAM}/git/ref/tags/{tag}')['object']
    for _ in range(5):
        if obj['type'] != 'tag':
            break
        obj = api(f'repos/{UPSTREAM}/git/tags/{obj["sha"]}')['object']
    require(obj['type'] == 'commit', 'Tag must resolve to a commit')
    commit = obj['sha']
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        subprocess.run(['gh', 'release', 'download', tag, '--repo', UPSTREAM,
                        '--pattern', 'release.json', '--pattern', 'SHA256SUMS',
                        '--pattern', f'probl-{tag[1:]}-source.tar.gz', '--dir', temporary], check=True)
        manifest = json.loads((folder / 'release.json').read_text())
        validate_manifest(manifest, tag, commit)
        archive = folder / manifest['archive']
        require(hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['sha256'], 'Source checksum mismatch')
        expected = ''.join(f'{hashlib.sha256((folder / name).read_bytes()).hexdigest()}  {name}\n'
                           for name in [manifest['archive'], 'release.json'])
        require((folder / 'SHA256SUMS').read_text() == expected, 'Checksum manifest mismatch')
        for name in [manifest['archive'], 'release.json', 'SHA256SUMS']:
            subprocess.run(['gh', 'attestation', 'verify', str(folder / name),
                            '--repo', UPSTREAM,
                            '--signer-workflow', f'{UPSTREAM}/.github/workflows/release.yml',
                            '--source-ref', f'refs/tags/{tag}', '--source-digest', commit,
                            '--signer-digest', commit, '--deny-self-hosted-runners'], check=True)
    return manifest


def output(**values):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as file:
        for key, value in values.items():
            file.write(f'{key}={value}\n')


def prepare(tag, destination):
    latest = api(f'repos/{UPSTREAM}/releases/latest', missing=True)
    if not latest:
        output(ready='false')
        return
    if not tag:
        # Releases preceding this pipeline have no attestations. Wait for the
        # next release instead of accepting them through a weaker path.
        if not latest.get('immutable') or 'release.json' not in {a['name'] for a in latest['assets']}:
            print('Waiting for the first attested immutable release')
            output(ready='false')
            return
        tag = latest['tag_name']
    if version(tag) < version(latest['tag_name']):
        output(ready='false')
        return
    manifest = verified_release(tag)
    base = api(f'repos/{TAP}/git/ref/heads/main')['object']['sha']
    source = contents(FORMULA, base)
    if version(tag) < formula_version(source):
        output(ready='false')
        return
    if version(tag) == formula_version(source):
        current = contents(METADATA, base, missing=True)
        require(current is not None and json.loads(current) == manifest, 'Same version has different or missing provenance')
        output(ready='false')
        return
    result = {'base': base, 'manifest': manifest, 'formula': render(source, manifest)}
    destination.write_text(json.dumps(result))
    output(ready='true')


def open_pr(prepared):
    base, manifest, formula = prepared['base'], prepared['manifest'], prepared['formula']
    require(api(f'repos/{TAP}/git/ref/heads/main')['object']['sha'] == base,
            'Main changed during verification; retry the updater')
    tag = manifest['tag']
    branch = f'release/probl-{tag}-{base[:12]}'
    tree = api(f'repos/{TAP}/git/trees', {
        'base_tree': api(f'repos/{TAP}/git/commits/{base}')['tree']['sha'],
        'tree': [{'path': path, 'mode': '100644', 'type': 'blob', 'content': text}
                 for path, text in [(FORMULA, formula), (METADATA, json.dumps(manifest, sort_keys=True) + '\n')]],
    })
    existing = api(f'repos/{TAP}/git/ref/heads/{branch}', missing=True)
    if existing:
        head = existing['object']['sha']
        existing_commit = api(f'repos/{TAP}/git/commits/{head}')
        require(existing_commit['tree']['sha'] == tree['sha'] and
                [p['sha'] for p in existing_commit['parents']] == [base],
                'Existing release branch contains unexpected changes')
        require(contents(FORMULA, head) == formula and
                contents(METADATA, head) == json.dumps(manifest, sort_keys=True) + '\n',
                'Existing release branch was modified')
    else:
        commit = api(f'repos/{TAP}/git/commits', {'message': f'probl {tag[1:]}',
                                               'tree': tree['sha'], 'parents': [base]})
        api(f'repos/{TAP}/git/refs', {'ref': f'refs/heads/{branch}', 'sha': commit['sha']})
    prs = api(f'repos/{TAP}/pulls?state=open&head=garlab:{branch}&base=main')
    if not prs:
        pr = api(f'repos/{TAP}/pulls', {
            'title': f'probl {tag[1:]}', 'head': branch, 'base': 'main',
            'body': f'Update from the verified immutable [Probl {tag} release](https://github.com/{UPSTREAM}/releases/tag/{tag}).\n\n'
                    f'Source commit: `{manifest["commit"]}`. SHA-256 and GitHub build provenance were verified. '
                    'The tap will build, test and publish bottles automatically after CI passes.',
        })
        print(pr['html_url'])
    else:
        print(prs[0]['html_url'])


def validate_candidate(pr, run, base, bot):
    require(run['event'] == 'pull_request' and run['conclusion'] == 'success' and
            run['path'] == '.github/workflows/tests.yml' and run['head_repository']['full_name'] == TAP,
            'Not a successful trusted tap PR workflow')
    require(pr['state'] == 'open' and not pr['draft'] and pr['user']['login'] == bot,
            'Only open release-bot PRs can be published automatically')
    require(pr['head']['repo']['full_name'] == TAP and pr['base']['ref'] == 'main' and
            pr['base']['repo']['full_name'] == TAP and pr['base']['sha'] == base,
            'Unexpected repository or stale base')
    require(pr['head']['sha'] == run['head_sha'], 'PR changed since the tested commit')


def gate(run_id):
    require(re.fullmatch(r'[1-9][0-9]*', str(run_id)), 'Invalid workflow run ID')
    run = api(f'repos/{TAP}/actions/runs/{run_id}')
    # Get associated PRs from the API, not an untrusted artifact or PR body.
    prs = api(f'repos/{TAP}/commits/{run["head_sha"]}/pulls')
    candidates = [p for p in prs if p['state'] == 'open' and p['head']['sha'] == run['head_sha']]
    if not candidates:
        print('No open PR at this commit; nothing to publish')
        output(ready='false')
        return
    require(len(candidates) == 1, 'Ambiguous PR association')
    pr = api(f'repos/{TAP}/pulls/{candidates[0]["number"]}')
    bot = os.environ['RELEASE_BOT_LOGIN']
    require(bot.endswith('[bot]'), 'Configure RELEASE_BOT_LOGIN for the GitHub App')
    if pr['user']['login'] != bot:
        print('Not a release-bot PR; publication remains manual')
        output(ready='false')
        return
    base = api(f'repos/{TAP}/git/ref/heads/main')['object']['sha']
    validate_candidate(pr, run, base, bot)
    head = pr['head']['sha']
    commit = api(f'repos/{TAP}/git/commits/{head}')
    require([p['sha'] for p in commit['parents']] == [base], 'Release PR must be one commit on current main')
    comparison = api(f'repos/{TAP}/compare/{base}...{head}')
    require({f['filename'] for f in comparison['files']} == {FORMULA, METADATA} and
            all(f['status'] in ['added', 'modified'] for f in comparison['files']),
            'Release PR contains changes outside the formula and provenance record')
    manifest = json.loads(contents(METADATA, head))
    tag = manifest['tag']
    version(tag)
    require(pr['head']['ref'] == f'release/probl-{tag}-{base[:12]}', 'Unexpected release branch')
    require(manifest == verified_release(tag), 'PR provenance differs from verified release')
    source = contents(FORMULA, base)
    require(version(tag) > formula_version(source), 'Refusing a duplicate or older formula version')
    require(contents(FORMULA, head) == render(source, manifest), 'Formula contains unapproved Ruby changes')
    latest = api(f'repos/{UPSTREAM}/releases/latest')
    require(version(tag) >= version(latest['tag_name']), 'A newer upstream release is available')
    runs = api(f'repos/{TAP}/actions/workflows/tests.yml/runs?event=pull_request&head_sha={head}&per_page=100')['workflow_runs']
    require(runs and max(runs, key=lambda r: r['id'])['id'] == int(run_id), 'A newer CI run exists')
    artifacts = api(f'repos/{TAP}/actions/runs/{run_id}/artifacts')['artifacts']
    prefix = f'bottles_{run_id}_{run["run_attempt"]}_'
    require({a['name'] for a in artifacts if not a['expired'] and a['name'].startswith(prefix)} ==
            {prefix + platform for platform in ['macos-26', 'macos-15-intel', 'ubuntu-latest']}, 'Missing bottle artifacts')
    output(ready='true', pr=pr['number'], head=head, base=base, tag=tag,
           run_id=run_id, attempt=run['run_attempt'])


def bottle_assets(folder, tag):
    version(tag)
    root_url = f'https://github.com/{TAP}/releases/download/probl-{tag[1:]}'
    assets = {}
    for metadata in folder.glob('*.bottle.json'):
        data = json.loads(metadata.read_text())
        require(set(data) == {'garlab/tap/probl'}, 'Unexpected formula in bottle metadata')
        formula = data['garlab/tap/probl']['formula']
        require(formula['name'] == 'probl' and formula['pkg_version'] == tag[1:] and
                formula['path'] == 'Library/Taps/garlab/homebrew-tap/Formula/probl.rb' and
                formula['tap_git_path'] == FORMULA, 'Unexpected formula path or version')
        bottle = data['garlab/tap/probl']['bottle']
        require(type(bottle['rebuild']) is int and bottle['rebuild'] == 0, 'Unexpected bottle rebuild')
        require(set(bottle['tags']) <= {'arm64_tahoe', 'sequoia', 'x86_64_linux'}, 'Unexpected bottle platform')
        require(bottle['root_url'] == root_url, 'Unexpected bottle destination')
        for entry in bottle['tags'].values():
            remote, local = entry['filename'], entry['local_filename']
            require(re.fullmatch(r'probl-' + re.escape(tag[1:]) + r'\.[a-z0-9_]+\.bottle(?:\.[0-9]+)?\.tar\.gz', remote),
                    'Unexpected bottle filename')
            require(local == remote.replace('probl-', 'probl--', 1) and
                    not (folder/local).is_symlink(), 'Unsafe local bottle path')
            sha = hashlib.sha256((folder/local).read_bytes()).hexdigest()
            require(sha == entry['sha256'], 'Bottle checksum mismatch')
            require(remote not in assets or assets[remote]['sha256'] == sha, 'Conflicting bottle metadata')
            assets[remote] = {'path': folder/local, 'sha256': sha}
    require(len(assets) == 3, 'Expected all three platform bottles')
    return assets


def upload_bottles(folder, tag, base):
    assets = bottle_assets(folder, tag)
    release_tag = 'probl-' + tag[1:]
    existing = api(f'repos/{TAP}/releases/tags/{release_tag}', missing=True)
    if not existing:
        subprocess.run(['gh', 'release', 'create', release_tag, '--repo', TAP,
                        '--target', base, '--draft', '--title', 'Probl ' + tag[1:],
                        '--notes', f'Bottles for https://github.com/{UPSTREAM}/releases/tag/{tag}'], check=True)
        existing = api(f'repos/{TAP}/releases/tags/{release_tag}')
    known = {asset['name'] for asset in existing['assets']}
    require(known <= assets.keys(), 'Bottle release contains unexpected assets')
    for name, asset in assets.items():
        if name in known:
            with tempfile.TemporaryDirectory() as temporary:
                subprocess.run(['gh', 'release', 'download', release_tag, '--repo', TAP,
                                '--pattern', name, '--dir', temporary], check=True)
                require(hashlib.sha256((Path(temporary)/name).read_bytes()).hexdigest() == asset['sha256'],
                        'Existing bottle differs; refusing to overwrite it')
        else:
            require(existing['draft'], 'Published bottle release is incomplete; refusing to modify it')
            # gh uses the local basename as the release asset name.
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary)/name
                path.write_bytes(asset['path'].read_bytes())
                subprocess.run(['gh', 'release', 'upload', release_tag, str(path), '--repo', TAP], check=True)


def publish_bottles(tag):
    version(tag)
    release_tag = 'probl-' + tag[1:]
    if api(f'repos/{TAP}/releases/tags/{release_tag}')['draft']:
        subprocess.run(['gh', 'release', 'edit', release_tag, '--repo', TAP, '--draft=false'], check=True)


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'prepare':
        prepare(os.environ.get('RELEASE_TAG', ''), Path(sys.argv[2]))
    elif command == 'open-pr':
        open_pr(json.loads(Path(sys.argv[2]).read_text()))
    elif command == 'gate':
        gate(sys.argv[2])
    elif command == 'check-bottles':
        bottle_assets(Path(sys.argv[2]), sys.argv[3])
    elif command == 'upload-bottles':
        upload_bottles(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif command == 'publish-bottles':
        publish_bottles(sys.argv[2])
    elif command == 'recheck':
        pr = api(f'repos/{TAP}/pulls/{sys.argv[2]}')
        require(pr['state'] == 'open' and pr['head']['sha'] == sys.argv[3] and
                api(f'repos/{TAP}/git/ref/heads/main')['object']['sha'] == sys.argv[4],
                'PR or main changed during publication; refusing to push')
    else:
        raise ValueError('Unknown command')
