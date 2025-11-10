package com.gifpt.security.auth.service;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;

@Service
public class JwtService {

  private final SecretKey key;
  private final long expiresInMs;

  public JwtService(
      @Value("${gifpt.jwt.secret}") String secret,
      @Value("${gifpt.jwt.expires-in-ms}") long expiresInMs
  ) {
    this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    this.expiresInMs = expiresInMs;
  }

  public String generateToken(String username, Map<String, Object> claims) {
    long now = System.currentTimeMillis();
    return Jwts.builder()
        .subject(username)
        .claims(claims)
        .issuedAt(new Date(now))
        .expiration(new Date(now + expiresInMs))
        .signWith(key)
        .compact();
  }

  public String extractUsername(String token) {
    return Jwts.parser().verifyWith(key).build()
        .parseSignedClaims(token).getPayload().getSubject();
  }

  public boolean isValid(String token, String expectedUsername) {
    try {
      var parsed = Jwts.parser().verifyWith(key).build().parseSignedClaims(token);
      var sub = parsed.getPayload().getSubject();
      var exp = parsed.getPayload().getExpiration();
      return sub != null && sub.equals(expectedUsername) && exp.after(new Date());
    } catch (Exception e) {
      return false;
    }
  }
}
