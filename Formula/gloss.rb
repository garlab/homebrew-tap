class Gloss < Formula
  desc "Terminal viewer for Markdown, math, diagrams, images, and code"
  homepage "https://github.com/garlab/gloss"
  url "https://github.com/garlab/gloss/releases/download/v0.1.1/gloss-0.1.1-source.tar.gz"
  sha256 "87ee340f519eef52517536b675823ffe7a17bbd27ba4771d37d1b17772a72edb"
  license "MIT"

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/gloss-0.1.1"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "a9460d5a37bd50258fad0bec910b433b65cc167d2ce181d42e34d1ac11a9271a"
    sha256 cellar: :any,                 x86_64_linux: "292b26d32cffb5e8a885aa9310274acaa3f3f7e1bab73d2e296af7486a9a35d5"
  end

  depends_on "rust" => :build

  deny_network_access!

  def fetch
    system "cargo", "fetch", *std_cargo_fetch_args
  end

  def install
    system "cargo", "install", *std_cargo_args
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/gloss --version")
    (testpath/"sample.md").write("# Hello\n\nA **small** document.\n")
    assert_match "Hello", shell_output("#{bin}/gloss --output text sample.md")
    assert_equal (testpath/"sample.md").read, shell_output("#{bin}/gloss --output source sample.md")
  end
end
