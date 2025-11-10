package com.gifpt.analysis.service;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.JobStatus;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Service
@RequiredArgsConstructor
public class AnalysisJobService {
  private final AnalysisJobRepository repo;

  public AnalysisJob markRunning(long jobId) {
    var job = repo.findById(jobId).orElseThrow();
    job.setStatus(JobStatus.RUNNING);
    job.setStartedAt(Instant.now());
    return repo.save(job);
  }

  public AnalysisJob completeSuccess(long jobId, String resultUrl, String summary) {
    var job = repo.findById(jobId).orElseThrow();
    job.setStatus(JobStatus.SUCCESS);
    job.setResultUrl(resultUrl);
    job.setSummary(summary);
    job.setFinishedAt(Instant.now());
    return repo.save(job);
  }

  public AnalysisJob completeFailed(long jobId, String errorMessage) {
    var job = repo.findById(jobId).orElseThrow();
    job.setStatus(JobStatus.FAILED);
    job.setErrorMessage(errorMessage);
    job.setFinishedAt(Instant.now());
    return repo.save(job);
  }
}
