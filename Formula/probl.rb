class Probl < Formula
  desc "Probabilistic programming language for models and forecasts"
  homepage "https://probl.dev"
  url "https://github.com/garlab/probl/releases/download/v0.3.3/probl-0.3.3-source.tar.gz"
  sha256 "9b250e50744988b7d08fc7f748f2c176c3add242367713332eca9bb2ddcda5ad"
  license any_of: ["MIT", "Apache-2.0"]

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/probl-0.3.3"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "4cb9d626096f0062f9329f78ec30a8257b81fcb5fdeab9d4a06f845bee05499e"
    sha256 cellar: :any,                 x86_64_linux: "0f2303d20c3575aedc1966f2e761f57fc28285131438c4a86b00c342bb1e568a"
  end

  depends_on "rust" => :build

  deny_network_access!

  def fetch
    system "cargo", "fetch", *std_cargo_fetch_args
  end

  def install
    system "cargo", "install", *std_cargo_args(path: "crates/probl-cli")
  end

  test do
    (testpath/"model.probl").write <<~EOS
      let total ~ 2d6
      report total >= 10 as "Rolling 10 or more"
    EOS
    assert_match "16.67%", shell_output("#{bin}/probl run model.probl")
  end
end
