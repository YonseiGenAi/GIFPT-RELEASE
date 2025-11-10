package com.gifpt.security.auth.service;

import com.gifpt.user.domain.User;
import com.gifpt.user.repository.UserRepository;
import org.springframework.security.core.userdetails.*;
import org.springframework.stereotype.Service;

@Service
public class CustomUserDetailsService implements UserDetailsService {
  private final UserRepository repo;
  public CustomUserDetailsService(UserRepository repo) { this.repo = repo; }

  @Override
  public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
    User u = repo.findByEmail(email)
        .orElseThrow(() -> new UsernameNotFoundException("No user: " + email));
    boolean locked = !"ACTIVE".equals(u.getStatus());
    return org.springframework.security.core.userdetails.User
        .withUsername(u.getEmail())
        .password(u.getPasswordHash())
        .roles("USER")
        .accountLocked(locked)
        .build();
  }
}
