package com.gifpt.workspace.repository;

import com.gifpt.workspace.domain.Workspace;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface WorkspaceRepository extends JpaRepository<Workspace, Long> {

    Optional<Workspace> findByAnalysisJobId(Long jobId);
}
