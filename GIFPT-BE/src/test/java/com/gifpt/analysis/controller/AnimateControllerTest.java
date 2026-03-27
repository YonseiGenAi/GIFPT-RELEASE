package com.gifpt.analysis.controller;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.AnalysisStatus;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import com.gifpt.file.service.S3StorageService;
import com.gifpt.security.auth.user.CustomUserPrincipal;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClient;

import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.mockito.Mockito.lenient;

@ExtendWith(MockitoExtension.class)
class AnimateControllerTest {

    @Mock
    private S3StorageService s3StorageService;

    @Mock
    private AnalysisJobRepository analysisJobRepository;

    @Mock(answer = org.mockito.Answers.RETURNS_DEEP_STUBS)
    private RestClient.Builder restClientBuilder;

    @InjectMocks
    private AnimateController controller;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(controller, "s3Bucket", "gifpt-demo");
        ReflectionTestUtils.setField(controller, "aiServerBaseUrl", "http://django:8000");
    }

    // ---- Static utility method tests (no mocks needed) ----

    @Test
    void normalizeSlug_validInput_passesThrough() {
        assertThat(AnimateController.normalizeSlug("bubble_sort")).isEqualTo("bubble_sort");
    }

    @Test
    void normalizeSlug_spaces_replacedWithUnderscore() {
        assertThat(AnimateController.normalizeSlug("bubble sort")).isEqualTo("bubble_sort");
    }

    @Test
    void normalizeSlug_aStar_expandedToAstar() {
        assertThat(AnimateController.normalizeSlug("A*")).isEqualTo("a_star");
    }

    @Test
    void normalizeSlug_floydWarshall_normalized() {
        assertThat(AnimateController.normalizeSlug("Floyd-Warshall")).isEqualTo("floyd_warshall");
    }

    @Test
    void normalizeSlug_pathTraversal_sanitized() {
        String result = AnimateController.normalizeSlug("../../etc/passwd");
        assertThat(result).doesNotContain(".", "/");
    }

    @Test
    void normalizeSlug_truncatedAt64() {
        String long_name = "a".repeat(100);
        assertThat(AnimateController.normalizeSlug(long_name)).hasSize(64);
    }

    @Test
    void normalizeSlug_empty_returnsEmpty() {
        assertThat(AnimateController.normalizeSlug("")).isEmpty();
    }

    @Test
    void normalizeSlug_nullInput_returnsEmpty() {
        assertThat(AnimateController.normalizeSlug(null)).isEmpty();
    }

    @Test
    void s3KeyForSlug_deterministicOutput() {
        // Same input → same SHA-256 hash every time
        String key1 = AnimateController.s3KeyForSlug("bubble_sort");
        String key2 = AnimateController.s3KeyForSlug("bubble_sort");
        assertThat(key1).isEqualTo(key2);
    }

    @Test
    void s3KeyForSlug_startsWithAnimationsPrefix() {
        assertThat(AnimateController.s3KeyForSlug("bubble_sort")).startsWith("animations/");
        assertThat(AnimateController.s3KeyForSlug("bubble_sort")).endsWith(".mp4");
    }

    @Test
    void s3KeyForSlug_differentSlugs_differentKeys() {
        assertThat(AnimateController.s3KeyForSlug("bubble_sort"))
                .isNotEqualTo(AnimateController.s3KeyForSlug("quick_sort"));
    }

    // ---- Controller endpoint tests ----

    @Test
    void animate_cacheHit_returns200WithVideoUrl() {
        when(s3StorageService.objectExists(anyString())).thenReturn(true);

        ResponseEntity<?> resp = controller.animate("bubble_sort", null);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(resp.getHeaders().getFirst("X-Cache")).isEqualTo("HIT");
        @SuppressWarnings("unchecked")
        Map<String, Object> body = (Map<String, Object>) resp.getBody();
        assertThat(body).containsKey("videoUrl");
        assertThat(body.get("status")).isEqualTo("SUCCESS");
    }

    @Test
    void animate_cacheMiss_anonymous_returns401() {
        when(s3StorageService.objectExists(anyString())).thenReturn(false);

        ResponseEntity<?> resp = controller.animate("bubble_sort", null /* anonymous */);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
        assertThat(resp.getHeaders().getFirst("X-Cache")).isEqualTo("MISS");
        @SuppressWarnings("unchecked")
        Map<String, Object> body = (Map<String, Object>) resp.getBody();
        assertThat(body.get("error")).isEqualTo("login_required");
    }

    @Test
    void animate_cacheMiss_authenticated_returns202WithJobId() {
        when(s3StorageService.objectExists(anyString())).thenReturn(false);

        // Mock job save
        AnalysisJob savedJob = AnalysisJob.builder()
                .userId(42L)
                .status(AnalysisStatus.PENDING)
                .prompt("bubble sort")
                .build();
        // Simulate auto-generated ID
        when(analysisJobRepository.save(any(AnalysisJob.class))).thenAnswer(inv -> {
            AnalysisJob j = inv.getArgument(0);
            // Reflect id
            ReflectionTestUtils.setField(j, "id", 99L);
            return j;
        });

        // RETURNS_DEEP_STUBS handles the full builder chain automatically

        CustomUserPrincipal user = mock(CustomUserPrincipal.class);
        when(user.getId()).thenReturn(42L);

        ResponseEntity<?> resp = controller.animate("bubble sort", user);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.ACCEPTED);
        assertThat(resp.getHeaders().getFirst("X-Cache")).isEqualTo("MISS");
        @SuppressWarnings("unchecked")
        Map<String, Object> body = (Map<String, Object>) resp.getBody();
        assertThat(body).containsKey("jobId");
        assertThat(body.get("status")).isEqualTo("PENDING");
    }

    @Test
    void animate_invalidSlug_returns400() {
        // All non-ASCII → empty slug after normalization
        ResponseEntity<?> resp = controller.animate("버블정렬", null);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void getStatus_jobFound_ownerMatches_returnsStatus() {
        AnalysisJob job = AnalysisJob.builder()
                .userId(42L)
                .status(AnalysisStatus.SUCCESS)
                .resultUrl("https://s3.example.com/video.mp4")
                .build();
        ReflectionTestUtils.setField(job, "id", 1L);

        when(analysisJobRepository.findById(1L)).thenReturn(Optional.of(job));

        CustomUserPrincipal user = mock(CustomUserPrincipal.class);
        when(user.getId()).thenReturn(42L);

        ResponseEntity<?> resp = controller.getStatus(1L, user);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.OK);
        @SuppressWarnings("unchecked")
        Map<String, Object> body = (Map<String, Object>) resp.getBody();
        assertThat(body.get("status")).isEqualTo("SUCCESS");
        assertThat(body.get("resultUrl")).isEqualTo("https://s3.example.com/video.mp4");
    }

    @Test
    void getStatus_wrongOwner_returns403() {
        AnalysisJob job = AnalysisJob.builder()
                .userId(99L)  // different owner
                .status(AnalysisStatus.PENDING)
                .build();
        ReflectionTestUtils.setField(job, "id", 1L);

        when(analysisJobRepository.findById(1L)).thenReturn(Optional.of(job));

        CustomUserPrincipal user = mock(CustomUserPrincipal.class);
        when(user.getId()).thenReturn(42L);  // different from job owner

        ResponseEntity<?> resp = controller.getStatus(1L, user);

        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.FORBIDDEN);
    }
}
