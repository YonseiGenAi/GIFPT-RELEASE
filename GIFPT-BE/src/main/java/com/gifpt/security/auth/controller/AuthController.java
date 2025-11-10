package com.gifpt.security.auth.controller;

import com.gifpt.user.domain.User;
import com.gifpt.user.repository.UserRepository;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;
import com.gifpt.security.auth.service.JwtService;
import com.gifpt.security.auth.service.RefreshTokenService;

import jakarta.servlet.http.HttpServletResponse;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

  private final AuthenticationManager authManager;
  private final JwtService jwtService;
  private final UserRepository userRepo;
  private final PasswordEncoder encoder;
  private final RefreshTokenService refreshService;

  public AuthController(
      AuthenticationManager am,
      JwtService js,
      UserRepository ur,
      PasswordEncoder pe,
      RefreshTokenService rs
  ) {
    this.authManager = am;
    this.jwtService = js;
    this.userRepo = ur;
    this.encoder = pe;
    this.refreshService = rs;
  }

  public record SignupReq(String email, String password, String displayName) {}
  public record LoginReq(String email, String password) {}

  @PostMapping("/signup")
  public ResponseEntity<?> signup(@RequestBody SignupReq req, HttpServletResponse res) {
    if (userRepo.existsByEmail(req.email())) {
      return ResponseEntity.badRequest().body(Map.of("error", "email already exists"));
    }
    User u = new User();
    u.setEmail(req.email());
    u.setPasswordHash(encoder.encode(req.password()));
    u.setDisplayName(req.displayName());
    userRepo.save(u);

    String access = jwtService.generateToken(u.getEmail(), Map.of("role","USER","name",u.getDisplayName()));
    String refresh = refreshService.issue(u, 7);

    ResponseCookie cookie = ResponseCookie.from("refreshToken", refresh)
        .httpOnly(true)
        .secure(false) // 운영에서 https면 true 권장
        .path("/")
        .maxAge(7*24*60*60)
        .sameSite("Lax")
        .build();
    res.addHeader("Set-Cookie", cookie.toString());

    return ResponseEntity.ok(Map.of("accessToken", access));
  }

  @PostMapping("/login")
  public ResponseEntity<?> login(@RequestBody LoginReq req, HttpServletResponse res) {
    Authentication auth = authManager.authenticate(
        new UsernamePasswordAuthenticationToken(req.email(), req.password())
    );
    String email = auth.getName();
    User user = userRepo.findByEmail(email).orElseThrow();
    String access = jwtService.generateToken(user.getEmail(), Map.of("role","USER","name",user.getDisplayName()));
    String refresh = refreshService.issue(user, 7);

    ResponseCookie cookie = ResponseCookie.from("refreshToken", refresh)
        .httpOnly(true)
        .secure(false) // prod: true
        .path("/")
        .maxAge(7*24*60*60)
        .sameSite("Lax")
        .build();
    res.addHeader("Set-Cookie", cookie.toString());

    return ResponseEntity.ok(Map.of(
        "accessToken", access
      )
    );
  }

  @PostMapping("/refresh")
  public ResponseEntity<?> refresh(@CookieValue("refreshToken") String rawRefresh) {
    var token = refreshService.validate(rawRefresh)
        .orElseThrow(() -> new RuntimeException("Invalid refresh token"));
    var user = token.getUser();
    String newAccess = jwtService.generateToken(user.getEmail(), Map.of("role","USER","name",user.getDisplayName()));
    return ResponseEntity.ok(Map.of("accessToken", newAccess));
  }

  @PostMapping("/logout")
  public ResponseEntity<?> logout(@CookieValue(value="refreshToken", required=false) String rawRefresh) {
    if (rawRefresh != null) refreshService.revoke(rawRefresh);
    // 쿠키 제거
    ResponseCookie delete = ResponseCookie.from("refreshToken", "").httpOnly(true).path("/").maxAge(0).build();
    return ResponseEntity.noContent()
      .header("Set-Cookie", delete.toString())
      .build();
  }

  @GetMapping("/me")
  public ResponseEntity<?> me(Authentication auth) {
    return ResponseEntity.ok(Map.of("email", auth.getName()));
  }
}
