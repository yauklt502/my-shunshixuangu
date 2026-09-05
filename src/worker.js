import { handleApi } from './lib/handler.mjs';

/**
 * Cloudflare Worker: static web/ + discipline API (free quote sources).
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/')) {
      return handleApi(request);
    }
    if (env.ASSETS) return env.ASSETS.fetch(request);
    return new Response('not found', { status: 404 });
  },
};
