class Gloss < Formula
  desc "Terminal viewer for Markdown, math, diagrams, images, and code"
  homepage "https://github.com/garlab/gloss"
  url "https://github.com/garlab/gloss/releases/download/v0.2.1/gloss-0.2.1-source.tar.gz"
  sha256 "38f05cfc65f1206fc2c1866f4ffc2681410d6a836ac1b1ba41963bdef31c6cc0"
  license "MIT"

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/gloss-0.2.1"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "941de407defbfdffad0bd620cbc3befdd50a3375dc9cacbf3271106961aca0e9"
    sha256 cellar: :any,                 x86_64_linux: "a392d4e1d62e0af8f981703a0e6a74d3608f9ebfe23508af073905e5d1d730bf"
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
