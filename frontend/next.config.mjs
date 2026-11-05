/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxy same-origin (ADR 0012): o browser fala só com a origem do frontend; /api/* é repassado
  // ao backend (incl. Set-Cookie), tornando o cookie de sessão first-party. BACKEND_URL é server-side.
  async rewrites() {
    // eslint-disable-next-line no-undef -- `process` é global do Node neste arquivo de config
    const backend = process.env.BACKEND_URL;
    return backend ? [{ source: "/api/:path*", destination: `${backend}/:path*` }] : [];
  },
};

export default nextConfig;
