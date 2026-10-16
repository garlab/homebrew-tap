class Probl < Formula
  desc "Probabilistic programming language for models and forecasts"
  homepage "https://probl.dev"
  url "https://github.com/garlab/probl/releases/download/v0.3.1/probl-0.3.1-source.tar.gz"
  sha256 "91ad767a54ab2d8d463417350abf1a0a6532b83332e740a7e3f4b7c57451b602"
  license any_of: ["MIT", "Apache-2.0"]

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/probl-0.3.1"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "5f53d80fa7e3ab6a052aca0f932f63781c06873e769b978974d41959717573b3"
    sha256 cellar: :any,                 x86_64_linux: "5cfa09b039bf428e0bfd43628e0cea1d93f9f17358af4daf4b4e5d0ae4404058"
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
