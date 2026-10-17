class Probl < Formula
  desc "Probabilistic programming language for models and forecasts"
  homepage "https://probl.dev"
  url "https://github.com/garlab/probl/releases/download/v0.3.2/probl-0.3.2-source.tar.gz"
  sha256 "50b046da426cc7defc5d2c0cbd5c48602fdac29f86329aae677638ebb97fcd2e"
  license any_of: ["MIT", "Apache-2.0"]

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/probl-0.3.2"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "cfd3154feb912e3ecfdca93df3dad5a0e0435bef66b2f05f303dcb1bdd6bfb35"
    sha256 cellar: :any,                 x86_64_linux: "e108322850697d61c22b0f5c11bd02cd35f54201a2307074af219e5ac9e337a5"
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
