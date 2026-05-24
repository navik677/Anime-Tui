# Maintainer: navik677 <navik677@gmail.com.com>
pkgname=anime-tui-git
pkgver=1.0.0.r3.g765ed20
pkgrel=1
pkgdesc="Елегантний та швидкий консольний (TUI) програвач для перегляду аніме (Anilibria, HDRezka, YummyAnime)"
arch=('any')
url="https://github.com/navik677/anime-tui"
license=('MIT')
depends=('python' 'python-requests' 'python-beautifulsoup4' 'python-lxml' 'mpv' 'fzf' 'yt-dlp')
makedepends=('git' 'python-build' 'python-installer' 'python-wheel' 'python-setuptools')
provides=("${pkgname%-git}")
conflicts=("${pkgname%-git}")
source=("git+${url}.git")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/${pkgname%-git}"
  printf "1.0.0.r%s.g%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short=7 HEAD)"
}

build() {
  cd "$srcdir/${pkgname%-git}"
  python -m build --wheel --no-isolation
}

package() {
  cd "$srcdir/${pkgname%-git}"
  python -m installer --destdir="$pkgdir" dist/*.whl
  install -Dm644 README.md "$pkgdir/usr/share/doc/${pkgname%-git}/README.md"
}
