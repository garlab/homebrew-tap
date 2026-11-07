# Garlab Tap

Homebrew formulae for the [Probl](https://probl.dev) language and the
[Gloss](https://github.com/garlab/gloss) terminal viewer:

```sh
brew install garlab/tap/probl
brew install garlab/tap/gloss
```

To update:

```sh
brew update
brew upgrade probl gloss
```

Formulae build from published source releases. Automated updates also produce
prebuilt packages (Homebrew's *bottles*) for Apple Silicon macOS and Linux
x86-64. Intel macOS has no prebuilt bottle: Homebrew no longer provides the Intel
Rust bottle needed by our build jobs. A source installation may also need to
build Rust; alternatively, install Rust with rustup and run
`cargo install probl --locked` or `cargo install gloss-cli --locked`. Other
supported platforms can build from source.

## How updates are published

The tap follows the GitHub releases of [Probl](https://github.com/garlab/probl/releases)
and [Gloss](https://github.com/garlab/gloss/releases). Before opening a
formula-update PR, automation verifies the release archive's checksum and build
provenance against the expected repository, workflow, tag and source commit. The
automated path accepts only immutable stable releases with the required
provenance assets, and only from the repository listed for that formula.

PR checks build and test the packages. A separate publisher verifies the exact
formula update and successful CI run before publishing bottles and updating the
tap. Retries accept existing package files only when their bytes match. The tap
also checks for releases on an hourly schedule to recover missed notifications,
which GitHub can delay by several hours. To start an update immediately, run
**Update formulae** in the Actions tab, or:

```sh
gh workflow run autobump.yml --ref main -f formula=gloss -f tag=vX.Y.Z
```

Omit `tag` to select the latest stable version. If another formula's update
advances `main` during a build, the publisher stops rather than publish an untested
merge. The next updater run opens a PR on current `main`, and the obsolete one can
be closed.

The [Probl release process](https://github.com/garlab/probl/blob/main/docs/releases.md)
and [Gloss release guide](https://github.com/garlab/gloss/blob/main/docs/releasing.md)
explain the source artifacts and distribution pipeline.

## Adding a formula

1. Give the project a `release.yml` that attests and publishes
   `<name>-X.Y.Z-source.tar.gz`, `release.json` and `SHA256SUMS` on an immutable
   release, as Probl's does. The tap verifies `release.yml` as the signer, so the
   attestation step belongs in that file and not in a reusable workflow.
2. Add the formula's repository to `FORMULAE` in `ci/releases.py`, and its name to
   the matrix, inputs and dispatch types in `autobump.yml`.
3. Add `<name>-*` to the target tags of the `bottle-tag-history` ruleset, which
   protects bottle tags from being moved or deleted.
4. Push a reviewed, source-only `Formula/<name>.rb` directly to `main`, using the
   tag archive URL of a version older than the first attested release. This
   bypasses the branch rules, and a PR would not work: `brew test-bot` audits
   formulae added by a PR with `--new`, whose notability rules reject young or
   small repositories.
5. Publish the next release. The updater replaces the formula's source and adds
   bottles; a formula's first version has none.
