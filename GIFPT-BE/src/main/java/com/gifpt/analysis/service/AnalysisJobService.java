package com.gifpt.analysis.service;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.AnalysisStatus;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import com.gifpt.analysis.dto.AnalysisCallbackDTO;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class AnalysisJobService {
  private final AnalysisJobRepository repo;

  public AnalysisJob markRunning(long jobId) {
    var job = repo.findById(jobId).orElseThrow();
    job.setStatus(AnalysisStatus.RUNNING);
    job.setStartedAt(Instant.now());
    return repo.save(job);
  }

  public AnalysisJob markPending(long jobId) {
    var job = repo.findById(jobId).orElseThrow();
    job.setStatus(AnalysisStatus.PENDING);
    // 굳이 시간 찍고 싶으면 createdAt / queuedAt 필드 추가 가능
    return repo.save(job);
  }

  public AnalysisJob completeSuccess(long jobId, String resultUrl, String summary) {
    var job = repo.findById(jobId).orElseThrow();
    job.setStatus(AnalysisStatus.SUCCESS);
    job.setResultUrl(resultUrl);
    job.setSummary(summary);
    job.setFinishedAt(Instant.now());
    return repo.save(job);
  }

  public AnalysisJob completeFailed(long jobId, String errorMessage) {
    var job = repo.findById(jobId).orElseThrow();
    job.setStatus(AnalysisStatus.FAILED);
    job.setErrorMessage(errorMessage);
    job.setFinishedAt(Instant.now());
    return repo.save(job);
  }

  public void markCompleted(Long jobId, AnalysisCallbackDTO dto) {
    // status가 null이면 일단 아무 것도 안 함
    if (dto.status() == null) {
      return;
    }

    switch (dto.status()) {
      case RUNNING -> markRunning(jobId);
      case SUCCESS -> completeSuccess(jobId, dto.resultUrl(), dto.summary());
      case FAILED -> completeFailed(jobId, dto.errorMessage());
      case PENDING -> markPending(jobId);
    }
  }
}
