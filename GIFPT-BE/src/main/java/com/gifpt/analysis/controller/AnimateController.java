package com.gifpt.analysis.controller;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.AnalysisStatus;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import com.gifpt.file.service.S3StorageService;
import com.gifpt.security.auth.user.CustomUserPrincipal;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/v1/animate")
@RequiredArgsConstructor
public class AnimateController {

    private final S3StorageService s3StorageService;
    private final AnalysisJobRepository analysisJobRepository;
    private final RestClient.Builder restClientBuilder;

    @Value("${gifpt.s3.bucket}")
    private String s3Bucket;

    @Value("${gifpt.ai-server.base-url}")
    private String aiServerBaseUrl;

    /**
     * GET /api/v1/animate?algorithm={name}
     *
     * Anonymous: cache HIT → 200 + videoUrl; cache MISS → 401
     * Authenticated: cache HIT → 200 + videoUrl; cache MISS → 202 + jobId
     *
     * Response headers: X-Cache: HIT | MISS
     */
    @GetMapping
    public ResponseEntity<?> animate(
            @RequestParam String algorithm,
            @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        String slug = normalizeSlug(algorithm);
        if (slug.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "invalid_algorithm", "message", "Algorithm name is empty or invalid after normalization"));
        }

        String s3Key = s3KeyForSlug(slug);
        boolean cacheHit = s3StorageService.objectExists(s3Key);

        if (cacheHit) {
            String videoUrl = "https://" + s3Bucket + ".s3.amazonaws.com/" + s3Key;
            log.info("[ANIMATE] cache HIT slug={}", slug);
            return ResponseEntity.ok()
                    .header("X-Cache", "HIT")
                    .body(Map.of("status", "SUCCESS", "videoUrl", videoUrl));
        }

        // Cache MISS — anonymous users cannot trigger generation
        if (user == null) {
            log.info("[ANIMATE] cache MISS, anonymous user slug={}", slug);
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .header("X-Cache", "MISS")
                    .body(Map.of("error", "login_required", "message", "로그인 후 생성 가능"));
        }

        // Cache MISS + authenticated → create job + dispatch
        AnalysisJob job = AnalysisJob.builder()
                .userId(user.getId())
                .status(AnalysisStatus.PENDING)
                .prompt(algorithm)
                .build();
        analysisJobRepository.save(job);

        log.info("[ANIMATE] cache MISS, dispatching job_id={} slug={} userId={}", job.getId(), slug, user.getId());

        RestClient restClient = restClientBuilder.baseUrl(aiServerBaseUrl).build();
        restClient.post()
                .uri("/animate")
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("job_id", job.getId(), "algorithm", algorithm))
                .retrieve()
                .toBodilessEntity();

        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .header("X-Cache", "MISS")
                .body(Map.of("status", "PENDING", "jobId", job.getId()));
    }

    /**
     * GET /api/v1/animate/status/{jobId}
     *
     * Returns the current status and resultUrl of an animate job.
     * Only the job owner can poll.
     */
    @GetMapping("/status/{jobId}")
    public ResponseEntity<?> getStatus(
            @PathVariable Long jobId,
            @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        AnalysisJob job = analysisJobRepository.findById(jobId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Job not found"));

        if (user == null || !job.getUserId().equals(user.getId())) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("error", "forbidden"));
        }

        return ResponseEntity.ok(Map.of(
                "jobId", job.getId(),
                "status", job.getStatus().name(),
                "resultUrl", job.getResultUrl() != null ? job.getResultUrl() : "",
                "errorMessage", job.getErrorMessage() != null ? job.getErrorMessage() : ""
        ));
    }

    /**
     * Mirror of Python normalize_slug() — must produce identical output so
     * both sides compute the same S3 cache key.
     *
     * "A*"            -> "a_star"
     * "Floyd-Warshall"-> "floyd_warshall"
     * "bubble sort"   -> "bubble_sort"
     */
    static String normalizeSlug(String name) {
        if (name == null || name.isBlank()) return "";
        String s = name.toLowerCase();
        s = s.replace("*", "_star").replace("+", "_plus");
        s = s.replace("-", "_").replace("/", "_").replace(" ", "_");
        s = s.replaceAll("[^a-z0-9_]", "");
        s = s.replaceAll("_+", "_").replaceAll("^_+|_+$", "");
        return s.length() > 64 ? s.substring(0, 64) : s;
    }

    /**
     * Compute the deterministic S3 key for a normalized slug.
     * Must match Python: hashlib.sha256(slug.encode()).hexdigest()
     */
    static String s3KeyForSlug(String slug) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(slug.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder(64);
            for (byte b : digest) {
                hex.append(String.format("%02x", b));
            }
            return "animations/" + hex + ".mp4";
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }
}
