package com.gifpt.security.auth.service;

import com.gifpt.user.domain.User;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;
import com.gifpt.security.auth.repository.RefreshTokenRepository;
import com.gifpt.security.auth.jwt.RefreshToken;

import java.security.MessageDigest;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import java.util.UUID;

@Service
public class RefreshTokenService {
  private final RefreshTokenRepository repo;

  public RefreshTokenService(RefreshTokenRepository repo) {
    this.repo = repo;
  }

  private static String sha256(String str) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      byte[] hash = md.digest(str.getBytes());
      StringBuilder sb = new StringBuilder();
      for (byte b : hash) sb.append(String.format("%02x", b));
      return sb.toString();
    } catch (java.security.NoSuchAlgorithmException e) {
      throw new IllegalStateException("SHA-256 algorithm not available for hashing in sha256()", e);
    }
  }

  /** 원본 문자열 토큰을 발급하고, 해시만 DB에 저장 */
  public String issue(User user, int days) {
    String rawToken = UUID.randomUUID().toString();
    var token = new RefreshToken();
    token.setUser(user);
    token.setTokenHash(sha256(rawToken));
    token.setIssuedAt(Instant.now());
    token.setExpiresAt(Instant.now().plus(days, ChronoUnit.DAYS));
    token.setRevoked(false);
    repo.save(token);
    return rawToken;
  }

  public Optional<RefreshToken> validate(String rawToken) {
    String hash = sha256(rawToken);
    return repo.findByTokenHash(hash)
        .filter(t -> !t.isRevoked() && t.getExpiresAt().isAfter(Instant.now()));
  }

  @Transactional
  public void revoke(String rawToken) {
    validate(rawToken).ifPresent(t -> {
      t.setRevoked(true);
      repo.save(t);
    });
  }
}
