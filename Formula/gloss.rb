class Gloss < Formula
  desc "Terminal viewer for Markdown, math, diagrams, images, and code"
  homepage "https://github.com/garlab/gloss"
  url "https://github.com/garlab/gloss/releases/download/v0.2.2/gloss-0.2.2-source.tar.gz"
  sha256 "13770bc99d5545167e26346f2f42eb62e2d347df35e1d070240aa44778ceb295"
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
