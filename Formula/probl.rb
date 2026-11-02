class Probl < Formula
  desc "Probabilistic programming language for models and forecasts"
  homepage "https://probl.dev"
  url "https://github.com/garlab/probl/releases/download/v0.4.0/probl-0.4.0-source.tar.gz"
  sha256 "c848dd377d120ef0aa0800454da6d4f4779370673b54a9b28b36d3658016eee3"
  license any_of: ["MIT", "Apache-2.0"]

  bottle do
    root_url "https://github.com/garlab/homebrew-tap/releases/download/probl-0.4.0"
    sha256 cellar: :any_skip_relocation, arm64_tahoe:  "dcd5e5eec73ea6489bb1424675c6b10be8963eb24890e565c4cc417036770f17"
    sha256 cellar: :any,                 x86_64_linux: "909fb4ae82560aeb738164aa21a025892a0cd49bfb5e194990e41e116d3b633c"
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
