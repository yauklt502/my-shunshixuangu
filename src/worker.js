/**
 * Cloudflare Worker: serve web/ static assets.
 */
export default {
  fetch(request, env) {
    return env.ASSETS.fetch(request);
  },
};
