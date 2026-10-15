# Garlab Tap

Install the Probl command-line tool:

```sh
brew install garlab/tap/probl
```

To update:

```sh
brew update
brew upgrade probl
```

The formula builds from the published Probl source release. Automated updates
also produce prebuilt packages (Homebrew's *bottles*) for Apple Silicon macOS
and Linux x86-64. Intel macOS has no prebuilt bottle: Homebrew no longer
provides the Intel Rust bottle needed by our build jobs. A source installation
may also need to build Rust; alternatively, install Rust with rustup and run
`cargo install probl --locked`. Other supported platforms can build from source.
The initial v0.2.1 formula is available as a source build.

See [probl.dev](https://probl.dev) for the language guide and examples.

## How updates are published

The tap follows [Probl releases](https://github.com/garlab/probl/releases).
Before opening a formula-update PR, automation verifies the release archive's
checksum and build provenance against the expected repository, workflow, tag
and source commit. The automated path accepts only immutable stable releases
with the required provenance assets.

PR checks build and test the packages. A separate publisher verifies the exact
formula update and successful CI run before publishing bottles and updating the
tap. Retries accept existing package files only when their bytes match. The tap
also checks for releases hourly to recover missed notifications.

The [Probl release process](https://github.com/garlab/probl/blob/main/docs/releases.md)
explains the source artifacts and distribution pipeline.

## Contributing

Changes to build instructions, dependencies and tests are reviewed separately
from automated version updates. Contributor PRs do not receive publishing
credentials and are not automatically published through the release-bot path.

Work in the tap checkout reported by `brew --repository garlab/tap`. Useful
checks are:

```sh
python3 -m unittest discover -s ci -p 'test_*.py'
brew style Formula/probl.rb
brew install --build-from-source garlab/tap/probl
brew test garlab/tap/probl
```

The policy tests cover release verification, stale or fork PRs, unexpected
formula changes, unsafe package metadata and partial-upload recovery.

When reporting an installation problem, include the Probl version, operating
system, processor architecture and relevant Homebrew output.
