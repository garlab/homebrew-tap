class Gloss < Formula
  desc "Terminal viewer for Markdown, math, diagrams, images, and code"
  homepage "https://github.com/garlab/gloss"
  url "https://github.com/garlab/gloss/releases/download/v0.2.0/gloss-0.2.0-source.tar.gz"
  sha256 "31fe4913786a4eb946f509f0588b4e4c5576a68a61630a5e08bcdd67485798fb"
  license "MIT"

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/gloss-0.2.0"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "55a1efb06cd8357752cd80954f8c213f744c18fc5d476b9a3c4d7945bf67194b"
    sha256 cellar: :any,                 x86_64_linux: "d5496972b78ba1ef9dd0e2b7a06b3913fab1da5358ff8a8c6785acd050fa7cd3"
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
