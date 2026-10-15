import copy
import json
import re
from pathlib import Path
import unittest
from unittest.mock import patch
import releases as policy

TAG = 'v0.2.2'
COMMIT = 'a' * 40
BASE = 'b' * 40
HEAD = 'c' * 40
MANIFEST = {'schema': 1, 'tag': TAG, 'commit': COMMIT,
            'archive': 'probl-0.2.2-source.tar.gz', 'sha256': 'd' * 64}
BOT = 'probl-release[bot]'


class PolicyTests(unittest.TestCase):
    def test_find_release_includes_paginated_drafts(self):
        draft = {'id': 7, 'tag_name': 'v1.2.3', 'draft': True}
        responses = {
            f'repos/{policy.TAP}/releases/tags/v1.2.3': None,
            f'repos/{policy.TAP}/releases?per_page=100&page=1': [
                {'tag_name': 'v0.0.1', 'draft': False}] * 100,
            f'repos/{policy.TAP}/releases?per_page=100&page=2': [draft],
        }
        with patch.object(policy, 'api', side_effect=lambda path, **kw: responses[path]):
            self.assertEqual(policy.find_release('v1.2.3'), draft)

    def test_find_release_distinguishes_missing_and_published(self):
        with patch.object(policy, 'api', side_effect=[None, []]):
            self.assertIsNone(policy.find_release('v1.2.3'))
        published = {'id': 7, 'draft': False}
        with patch.object(policy, 'api', return_value=published) as api:
            self.assertEqual(policy.find_release('v1.2.3'), published)
            self.assertEqual(api.call_count, 1)

    def test_find_release_rejects_ambiguous_drafts(self):
        drafts = [{'id': n, 'tag_name': 'v1.2.3', 'draft': True} for n in [7, 8]]
        with patch.object(policy, 'api', side_effect=[None, drafts]):
            with self.assertRaisesRegex(ValueError, 'Multiple releases'):
                policy.find_release('v1.2.3')

    def test_bottle_draft_creation_upload_and_publication(self):
        import tempfile
        draft = {'id': 7, 'tag_name': 'probl-0.2.2', 'draft': True, 'assets': []}
        created = False
        def api(path, **kwargs):
            if path == f'repos/{policy.TAP}/releases/tags/probl-0.2.2':
                return None
            if path == f'repos/{policy.TAP}/releases?per_page=100&page=1':
                return [draft] if created else []
            raise AssertionError(path)
        def command(args, **kwargs):
            nonlocal created
            if args[1:3] == ['release', 'create']:
                self.assertFalse(created)
                created = True
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.bottles(folder)
            with patch.object(policy, 'api', side_effect=api), \
                 patch.object(policy.subprocess, 'run', side_effect=command) as run:
                policy.upload_bottles(folder, TAG, BASE)
                policy.publish_bottles(TAG)
                commands = [c.args[0] for c in run.call_args_list]
                self.assertEqual(sum(args[2] == 'upload' for args in commands), 2)
                self.assertEqual(commands[-1][1:4], ['release', 'edit', 'probl-0.2.2'])
                self.assertIn('--draft=false', commands[-1])

    def test_manifest_rejects_substitution_and_paths(self):
        policy.validate_manifest(MANIFEST, TAG, COMMIT)
        for key, value in [('commit', 'e'*40), ('tag', 'v0.2.3'), ('schema', 2),
                           ('archive', '../payload'), ('sha256', '"; system("bad")')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy.validate_manifest({**MANIFEST, key: value}, TAG, COMMIT)

    def test_formula_update_preserves_reviewed_ruby_and_removes_old_bottles(self):
        source = re.sub(r'^  url .*$', '  url "https://github.com/garlab/probl/archive/refs/tags/v0.2.1.tar.gz"',
                        (Path(__file__).parents[1]/policy.FORMULA).read_text(), flags=re.M)
        source = source.replace('  depends_on', '\n  bottle do\n    sha256 arm64_tahoe: "old"\n  end\n\n  depends_on', 1)
        result = policy.render(source, MANIFEST)
        self.assertNotIn('bottle do', result)
        self.assertIn(f'releases/download/{TAG}/{MANIFEST["archive"]}', result)
        self.assertIn('std_cargo_args(path: "crates/probl-cli")', result)
        self.assertIn('assert_match "16.67%"', result)

    def test_version_ordering_and_invalid_tags(self):
        self.assertGreater(policy.version('v0.10.0'), policy.version('v0.9.9'))
        for value in ['v1.2.3-rc1', 'v01.2.3', '../../x', 'v1.2.3\n']:
            with self.assertRaises(ValueError):
                policy.version(value)

    def candidate(self):
        pr = {'state': 'open', 'draft': False, 'user': {'login': BOT},
              'head': {'sha': HEAD, 'repo': {'full_name': policy.TAP},
                       'ref': f'release/probl-{TAG}-{BASE[:12]}'},
              'base': {'sha': BASE, 'ref': 'main', 'repo': {'full_name': policy.TAP}}, 'number': 7}
        run = {'id': 123, 'run_attempt': 1, 'event': 'pull_request', 'conclusion': 'success',
               'path': '.github/workflows/tests.yml', 'head_sha': HEAD,
               'head_repository': {'full_name': policy.TAP}}
        return pr, run

    def test_rejects_forks_stale_heads_wrong_workflows_and_failed_runs(self):
        pr, run = self.candidate()
        policy.validate_candidate(pr, run, BASE, BOT)
        for field, value in [('event', 'push'), ('conclusion', 'failure'),
                             ('path', '.github/workflows/evil.yml'), ('head_sha', 'e'*40)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                policy.validate_candidate(pr, {**run, field: value}, BASE, BOT)
        for section, field, value in [('head', 'repo', {'full_name': 'attacker/tap'}),
                                      ('base', 'sha', 'e'*40), ('user', 'login', 'attacker')]:
            changed = copy.deepcopy(pr)
            changed[section][field] = value
            with self.assertRaises(ValueError):
                policy.validate_candidate(changed, run, BASE, BOT)

    def gate_fixture(self, mutation=None):
        pr, run = self.candidate()
        source = re.sub(r'^  url .*$', '  url "https://github.com/garlab/probl/archive/refs/tags/v0.2.1.tar.gz"',
                        (Path(__file__).parents[1]/policy.FORMULA).read_text(), flags=re.M)
        formula = policy.render(source, MANIFEST)
        responses = {
            f'repos/{policy.TAP}/actions/runs/123': run,
            f'repos/{policy.TAP}/pulls/7': pr,
            f'repos/{policy.TAP}/commits/{HEAD}/pulls': [pr],
            f'repos/{policy.TAP}/git/ref/heads/main': {'object': {'sha': BASE}},
            f'repos/{policy.TAP}/git/commits/{HEAD}': {'parents': [{'sha': BASE}]},
            f'repos/{policy.TAP}/compare/{BASE}...{HEAD}': {'files': [
                {'filename': policy.FORMULA, 'status': 'modified'},
                {'filename': policy.METADATA, 'status': 'added'}]},
            f'repos/{policy.UPSTREAM}/releases/latest': {'tag_name': TAG},
            f'repos/{policy.TAP}/actions/workflows/tests.yml/runs?event=pull_request&head_sha={HEAD}&per_page=100': {'workflow_runs': [run]},
            f'repos/{policy.TAP}/actions/runs/123/artifacts': {'artifacts': [
                {'name': 'bottles_123_1_'+os, 'expired': False} for os in ['macos-26', 'ubuntu-latest']]},
        }
        files = {(policy.FORMULA, BASE): source, (policy.FORMULA, HEAD): formula,
                 (policy.METADATA, HEAD): json.dumps(MANIFEST)}
        if mutation:
            mutation(responses, files)
        with patch.dict('os.environ', {'RELEASE_BOT_LOGIN': BOT}), \
             patch.object(policy, 'api', side_effect=lambda path: responses[path]), \
             patch.object(policy, 'contents', side_effect=lambda path, ref: files[path, ref]), \
             patch.object(policy, 'verified_release', return_value=MANIFEST), \
             patch.object(policy, 'output') as output:
            policy.gate('123')
            output.assert_called_once_with(ready='true', pr=7, head=HEAD, base=BASE, tag=TAG, run_id='123', attempt=1)

    def test_upstream_verification_requires_immutable_release(self):
        with patch.object(policy, 'api', return_value={'draft': False, 'prerelease': False, 'immutable': False}), \
             patch.object(policy.subprocess, 'run') as command:
            with self.assertRaisesRegex(ValueError, 'immutable'):
                policy.verified_release(TAG)
            command.assert_not_called()

    def test_attestation_checks_bind_all_assets_to_workflow_tag_and_commit(self):
        import hashlib
        def command(args, **kwargs):
            if args[1:3] == ['release', 'download']:
                folder = Path(args[args.index('--dir') + 1])
                content = b'fixture archive'
                manifest = {**MANIFEST, 'sha256': hashlib.sha256(content).hexdigest()}
                (folder/manifest['archive']).write_bytes(content)
                (folder/'release.json').write_text(json.dumps(manifest))
                (folder/'SHA256SUMS').write_text(''.join(
                    f'{hashlib.sha256((folder/name).read_bytes()).hexdigest()}  {name}\n'
                    for name in [manifest['archive'], 'release.json']))
        responses = [
            {'draft': False, 'prerelease': False, 'immutable': True},
            {'object': {'type': 'commit', 'sha': COMMIT}},
        ]
        with patch.object(policy, 'api', side_effect=responses), \
             patch.object(policy.subprocess, 'run', side_effect=command) as run:
            policy.verified_release(TAG)
            verifies = [call.args[0] for call in run.call_args_list if call.args[0][1] == 'attestation']
            self.assertEqual(len(verifies), 3)
            for args in verifies:
                for flag, value in [('--repo', policy.UPSTREAM), ('--source-ref', 'refs/tags/' + TAG),
                                    ('--source-digest', COMMIT), ('--signer-digest', COMMIT),
                                    ('--signer-workflow', policy.UPSTREAM + '/.github/workflows/release.yml')]:
                    self.assertEqual(args[args.index(flag) + 1], value)
                self.assertIn('--deny-self-hosted-runners', args)

    def bottles(self, folder):
        import hashlib
        paths = []
        for platform in ['arm64_tahoe', 'x86_64_linux']:
            local = f'probl--0.2.2.{platform}.bottle.tar.gz'
            remote = local.replace('probl--', 'probl-', 1)
            (folder/local).write_bytes(platform.encode())
            data = {'garlab/tap/probl': {
                'formula': {'name': 'probl', 'pkg_version': '0.2.2', 'tap_git_path': policy.FORMULA,
                            'path': 'Library/Taps/garlab/homebrew-tap/Formula/probl.rb'},
                'bottle': {'root_url': f'https://github.com/{policy.TAP}/releases/download/probl-0.2.2',
                           'rebuild': 0, 'tags': {platform: {'filename': remote, 'local_filename': local,
                                                           'sha256': hashlib.sha256(platform.encode()).hexdigest()}}}}}
            path = folder/(platform + '.bottle.json')
            path.write_text(json.dumps(data))
            paths.append(path)
        return paths

    def test_bottles_reject_tampering_and_formula_path_changes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            paths = self.bottles(folder)
            self.assertEqual(len(policy.bottle_assets(folder, TAG)), 2)
            data = json.loads(paths[0].read_text())
            data['garlab/tap/probl']['formula']['path'] = '../malicious.rb'
            paths[0].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'formula path'):
                policy.bottle_assets(folder, TAG)
            self.bottles(folder)
            next(folder.glob('*.tar.gz')).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                policy.bottle_assets(folder, TAG)

    def test_bottles_require_each_supported_platform(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            paths = self.bottles(folder)
            paths[-1].unlink()
            with self.assertRaisesRegex(ValueError, 'Expected Apple Silicon'):
                policy.bottle_assets(folder, TAG)
            paths = self.bottles(folder)
            data = json.loads(paths[-1].read_text())
            bottle = data['garlab/tap/probl']['bottle']
            bottle['tags']['sequoia'] = bottle['tags'].pop('x86_64_linux')
            paths[-1].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Unexpected bottle platform'):
                policy.bottle_assets(folder, TAG)

    def test_bottle_upload_resumes_without_overwriting(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.bottles(folder)
            assets = policy.bottle_assets(folder, TAG)
            first = next(iter(assets))
            def command(args, **kwargs):
                if args[1:3] == ['release', 'download']:
                    destination = Path(args[args.index('--dir') + 1])/first
                    destination.write_bytes(assets[first]['path'].read_bytes())
            with patch.object(policy, 'find_release', return_value={'draft': True, 'assets': [{'name': first}]}), \
                 patch.object(policy.subprocess, 'run', side_effect=command) as run:
                policy.upload_bottles(folder, TAG, BASE)
                uploads = [c.args[0] for c in run.call_args_list if c.args[0][1:3] == ['release', 'upload']]
                self.assertEqual(len(uploads), 1)
                self.assertTrue(all('--clobber' not in args for args in uploads))
            def tampered(args, **kwargs):
                (Path(args[args.index('--dir') + 1])/first).write_bytes(b'wrong')
            with patch.object(policy, 'find_release', return_value={'draft': True, 'assets': [{'name': first}]}), \
                 patch.object(policy.subprocess, 'run', side_effect=tampered), \
                 self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
                policy.upload_bottles(folder, TAG, BASE)

    def test_gate_names_missing_expired_and_previous_attempt_artifacts(self):
        for kind in ['missing', 'expired', 'old-attempt']:
            def mutate(responses, files):
                artifacts = responses[f'repos/{policy.TAP}/actions/runs/123/artifacts']['artifacts']
                if kind == 'missing':
                    artifacts.pop()
                elif kind == 'expired':
                    artifacts[-1]['expired'] = True
                else:
                    artifacts[-1]['name'] = artifacts[-1]['name'].replace('_123_1_', '_123_0_')
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'missing=.*bottles_123_1_ubuntu-latest'):
                self.gate_fixture(mutate)

    def test_gate_accepts_only_exact_generated_update(self):
        self.gate_fixture()

    def test_gate_rejects_ruby_injection_and_workflow_edits(self):
        def ruby(responses, files):
            files[policy.FORMULA, HEAD] += '\nsystem "malicious"\n'
        def workflow(responses, files):
            responses[f'repos/{policy.TAP}/compare/{BASE}...{HEAD}']['files'].append(
                {'filename': '.github/workflows/tests.yml', 'status': 'modified'})
        def missing_bottle(responses, files):
            responses[f'repos/{policy.TAP}/actions/runs/123/artifacts']['artifacts'].pop()
        def new_run(responses, files):
            responses[f'repos/{policy.TAP}/actions/workflows/tests.yml/runs?event=pull_request&head_sha={HEAD}&per_page=100']['workflow_runs'].append({'id': 124})
        for mutation in [ruby, workflow, missing_bottle, new_run]:
            with self.subTest(mutation=mutation.__name__), self.assertRaises(ValueError):
                self.gate_fixture(mutation)


if __name__ == '__main__':
    unittest.main()
