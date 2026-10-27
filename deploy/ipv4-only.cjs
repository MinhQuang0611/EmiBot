// Force IPv4 for every DNS lookup: this machine has no working IPv6 route to hostingersite.com.
const dns = require("dns");
const orig = dns.lookup;
dns.lookup = function (host, opts, cb) {
  if (typeof opts === "function") { cb = opts; opts = {}; }
  if (typeof opts === "number") opts = { family: opts };
  return orig.call(dns, host, { ...opts, family: 4 }, cb);
};
