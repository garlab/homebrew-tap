class Gloss < Formula
  desc "Terminal viewer for Markdown, math, diagrams, images, and code"
  homepage "https://github.com/garlab/gloss"
  url "https://github.com/garlab/gloss/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "279224870ab8731b797d5b50caed95537428f421676d19bc9c87c14a87e2cb67"
  license "MIT"

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
