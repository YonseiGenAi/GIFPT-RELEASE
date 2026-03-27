package com.gifpt.security.auth.config;

import com.gifpt.security.auth.jwt.JwtAuthFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

  private final JwtAuthFilter jwtAuthFilter;
  private final UserDetailsService userDetailsService;
  private final PasswordEncoder passwordEncoder;

  public SecurityConfig(JwtAuthFilter jwtAuthFilter, UserDetailsService uds, PasswordEncoder pe) {
    this.jwtAuthFilter = jwtAuthFilter;
    this.userDetailsService = uds;
    this.passwordEncoder = pe;
  }

  @Bean
  public AuthenticationProvider authenticationProvider() {
    DaoAuthenticationProvider provider = new DaoAuthenticationProvider();
    provider.setUserDetailsService(userDetailsService);
    provider.setPasswordEncoder(passwordEncoder);
    return provider;
  }

  @Bean
  public AuthenticationManager authenticationManager(AuthenticationConfiguration cfg) throws Exception {
    return cfg.getAuthenticationManager();
  }

  @Bean
  SecurityFilterChain security(HttpSecurity http) throws Exception {
    http
      .csrf(csrf -> csrf.disable())
      .cors(Customizer.withDefaults())
      .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
      .authorizeHttpRequests(auth -> auth
        .requestMatchers(
          "/healthz",
          "/actuator/health",
          "/actuator/health/**",
          "/v3/api-docs",
          "/v3/api-docs/**",
          "/swagger-ui/**",
          "/swagger-ui.html",
          "/api/v1/auth/**",
          "/api/v1/analysis/*/complete",
          "/api/v1/analysis/**",
          "/v1/auth/**",
          "/api/v1/workspaces/**",
          "/api/v1/animate/**"
        ).permitAll()
        .anyRequest().authenticated()
      )
      .httpBasic(basic -> basic.disable())
      .formLogin(form -> form.disable())
      .authenticationProvider(authenticationProvider())
      .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

    return http.build();
  }

  @Bean
  org.springframework.web.cors.CorsConfigurationSource corsConfigurationSource(
  ) {
    var c = new org.springframework.web.cors.CorsConfiguration();
    c.setAllowedOrigins(java.util.List.of(
      "https://gifpt-front.vercel.app"
    ));
    c.setAllowedMethods(java.util.List.of("GET","POST","PUT","PATCH","DELETE","OPTIONS"));
    c.setAllowedHeaders(java.util.List.of("Authorization","Content-Type","X-Requested-With"));
    c.setExposedHeaders(java.util.List.of("Authorization","Set-Cookie"));
    c.setAllowCredentials(true);
    c.setMaxAge(3600L);
    var src = new org.springframework.web.cors.UrlBasedCorsConfigurationSource();
    src.registerCorsConfiguration("/**", c);
    return src;
  }
}
