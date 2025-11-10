package com.gifpt.analysis.controller;

import com.gifpt.analysis.domain.JobStatus;
import com.gifpt.analysis.service.AnalysisJobService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.gifpt.analysis.DTO.AnalysisCallbackDTO;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/analysis")
public class AnalysisCallbackController {

  private final AnalysisJobService service;

  @PostMapping("/{jobId}/complete")
  public ResponseEntity<?> complete(@PathVariable Long jobId,
                                    @RequestBody AnalysisCallbackDTO req) {
    if (req.status() == JobStatus.SUCCESS) {
      service.completeSuccess(jobId, req.resultUrl(), req.summary());
      return ResponseEntity.ok().build();
    } else if (req.status() == JobStatus.FAILED) {
      service.completeFailed(jobId, req.errorMessage());
      return ResponseEntity.ok().build();
    } else {
      return ResponseEntity.badRequest().body("status must be SUCCESS or FAILED");
    }
  }
}
