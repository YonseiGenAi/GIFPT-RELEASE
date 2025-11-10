package com.gifpt.analysis.repository;

import com.gifpt.analysis.domain.AnalysisJob;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, Long> {
}
