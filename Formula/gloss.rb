class Gloss < Formula
  desc "Terminal viewer for Markdown, math, diagrams, images, and code"
  homepage "https://github.com/garlab/gloss"
  url "https://github.com/garlab/gloss/releases/download/v0.2.3/gloss-0.2.3-source.tar.gz"
  sha256 "b0c9eeec49491948f394895ea6da3437bab36770d9929f1546748de44f08e44a"
  license "MIT"

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/gloss-0.2.3"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "197e47c0232cdbb69273e7bcefd8043629aef540aba2167b549cf854116580c7"
    sha256 cellar: :any,                 x86_64_linux: "16209bbdb2d6d57539cb5b9dc19dc2ed8459b7ea6baf57e4a2a14302e2383364"
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
