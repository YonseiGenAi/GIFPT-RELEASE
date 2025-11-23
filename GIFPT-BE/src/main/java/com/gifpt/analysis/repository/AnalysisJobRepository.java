package com.gifpt.analysis.repository;

import com.gifpt.analysis.domain.AnalysisJob;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, Long> {
    Optional<AnalysisJob> findByIdAndUserId(Long id, Long userId);
}
