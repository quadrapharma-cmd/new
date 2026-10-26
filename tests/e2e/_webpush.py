"""Test helpers for web push (w-pwa): a fake browser subscription (its own P-256 key pair and auth secret, like a real browser makes)
and the browser side of RFC 8291 — decrypt what the server sent to it. Used by e5_push_test.py and the J-SOCIAL-PWA journeys."""
import os, base64, struct
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def unb64u(s): return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))
def _hmac(k, d): h = hmac.HMAC(k, hashes.SHA256()); h.update(d); return h.finalize()

class FakeSubscription:
    def __init__(self, endpoint):
        self.key = ec.generate_private_key(ec.SECP256R1()); self.secret = os.urandom(16); self.endpoint = endpoint
        self.pub = self.key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    @property
    def p256dh(self): return b64u(self.pub)
    @property
    def auth(self): return b64u(self.secret)
    def json(self): return {'endpoint': self.endpoint, 'keys': {'p256dh': self.p256dh, 'auth': self.auth}}
    def decrypt(self, body):
        """aes128gcm (RFC 8188 header + RFC 8291 keys) → the plaintext bytes; raises when anything does not check out"""
        salt, rs, idlen = body[:16], struct.unpack('>I', body[16:20])[0], body[20]; as_pub = body[21:21 + idlen]; ct = body[21 + idlen:]
        assert idlen == 65 and rs >= 18 and len(ct) <= rs, 'bad header'
        shared = self.key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
        ikm = _hmac(_hmac(self.secret, shared), b'WebPush: info\x00' + self.pub + as_pub + b'\x01')
        prk = _hmac(salt, ikm)
        cek = _hmac(prk, b'Content-Encoding: aes128gcm\x00\x01')[:16]; nonce = _hmac(prk, b'Content-Encoding: nonce\x00\x01')[:12]
        pt = AESGCM(cek).decrypt(nonce, ct, None).rstrip(b'\x00')
        assert pt.endswith(b'\x02'), 'not the last record'
        return pt[:-1]
