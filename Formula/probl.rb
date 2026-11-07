class Probl < Formula
  desc "Probabilistic programming language for models and forecasts"
  homepage "https://probl.dev"
  url "https://github.com/garlab/probl/releases/download/v0.6.0/probl-0.6.0-source.tar.gz"
  sha256 "7d705d322632a854a5ab0b586b4b209c043ad5612da443e44d0ab15b1ac8d6b0"
  license any_of: ["MIT", "Apache-2.0"]

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/probl-0.6.0"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "e9568b3fc89fbf357edad802104c43ece5517314c250b1174ef64863b1978807"
    sha256 cellar: :any,                 x86_64_linux: "ecdf2315f3b8e6d25ae6d37c6273b9837039769faa9c7118226dacc76db9ca49"
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
