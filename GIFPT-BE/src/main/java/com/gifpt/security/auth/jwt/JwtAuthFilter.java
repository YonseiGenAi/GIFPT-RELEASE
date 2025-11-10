package com.gifpt.security.auth.jwt;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import com.gifpt.security.auth.service.JwtService;

import java.io.IOException;

@Component
public class JwtAuthFilter extends OncePerRequestFilter {

  private final JwtService jwtService;
  private final UserDetailsService userDetailsService;

  public JwtAuthFilter(JwtService jwtService, UserDetailsService uds) {
    this.jwtService = jwtService;
    this.userDetailsService = uds;
  }

  @Override
  protected boolean shouldNotFilter(@NonNull HttpServletRequest request) {
    String p = request.getServletPath();
    return p.equals("/healthz")
        || p.startsWith("/actuator/health")
        || p.equals("/swagger-ui.html")
        || p.startsWith("/swagger-ui")
        || p.equals("/v3/api-docs")
        || p.startsWith("/v3/api-docs")
        || p.equals("/v3/api-docs/swagger-config")
        || p.equals("/v3/api-docs.yaml")
        // 공개 인증/콜백 경로도 제외(원하면)
        || p.startsWith("/api/v1/auth/")
        || p.matches("^/api/v1/analysis/[^/]+/complete$");
  }

  @Override
  protected void doFilterInternal(@NonNull HttpServletRequest req, @NonNull HttpServletResponse res, @NonNull FilterChain chain)
      throws ServletException, IOException {

    String auth = req.getHeader("Authorization");
    if (auth != null && auth.startsWith("Bearer ")) {
      String token = auth.substring(7);
      try {
        String username = jwtService.extractUsername(token);
        if (username != null && SecurityContextHolder.getContext().getAuthentication() == null) {
          UserDetails ud = userDetailsService.loadUserByUsername(username);
          if (jwtService.isValid(token, ud.getUsername())) {
            var authToken = new UsernamePasswordAuthenticationToken(ud, null, ud.getAuthorities());
            authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(req));
            SecurityContextHolder.getContext().setAuthentication(authToken);
          }
        }
      } catch (Exception ignored) { }
    }
    chain.doFilter(req, res);
  }
}
