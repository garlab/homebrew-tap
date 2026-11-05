class Probl < Formula
  desc "Probabilistic programming language for models and forecasts"
  homepage "https://probl.dev"
  url "https://github.com/garlab/probl/releases/download/v0.5.0/probl-0.5.0-source.tar.gz"
  sha256 "391fd26a44658a6fb1560eb56a1f06111eba781ee5b9a5fb69d587db7f5cc772"
  license any_of: ["MIT", "Apache-2.0"]

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/probl-0.5.0"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "56fdca39c0dc14f3dfbeef0b4ecd93515df73aae2942d7f7843e1a8f80672a29"
    sha256 cellar: :any,                 x86_64_linux: "1e5072648eb97e7bd525078ad74c0627284e9650087fc0dea0ad603173c9d147"
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
