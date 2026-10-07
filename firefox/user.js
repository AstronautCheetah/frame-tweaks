// steam-frame-tweaks: Firefox anti-fingerprinting ("maximum" level)
// Applied at every Firefox start; values here override the Settings UI and Sync.

// Tor Browser-style fingerprinting resistance: common platform (Linux x86_64 instead
// of the Frame's rare aarch64), generic GPU/WebGL info, rounded screen size, UTC
// timezone, light color scheme, fixed fonts, reduced timer precision, and more.
user_pref("privacy.resistFingerprinting", true);
// Round the content area to common sizes (grey margins) so the VR desktop's unusual
// window size doesn't identify you.
user_pref("privacy.resistFingerprinting.letterboxing", true);
// Always ask for English pages without prompting (RFP otherwise asks per site).
user_pref("privacy.spoof_english", 2);

// WebRTC: don't expose local or non-default network addresses (matters with a VPN).
user_pref("media.peerconnection.ice.default_address_only", true);
user_pref("media.peerconnection.ice.no_host", true);
user_pref("media.peerconnection.ice.proxy_only_if_behind_proxy", true);

// Keep what's already on: strict tracking protection (blocks known fingerprinting
// scripts) and HTTPS-only mode.
user_pref("browser.contentblocking.category", "strict");
user_pref("privacy.fingerprintingProtection", true);
user_pref("dom.security.https_only_mode", true);
