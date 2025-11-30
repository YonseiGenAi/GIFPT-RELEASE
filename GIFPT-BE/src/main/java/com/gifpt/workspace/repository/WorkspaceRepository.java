package com.gifpt.workspace.repository;

import com.gifpt.workspace.domain.Workspace;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.util.Optional;

public interface WorkspaceRepository extends JpaRepository<Workspace, Long> {

    Optional<Workspace> findByAnalysisJobId(Long jobId);

    Page<Workspace> findByOwnerId(Long ownerId, Pageable pageable);
}
