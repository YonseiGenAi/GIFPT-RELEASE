package com.gifpt.file.repository;

import com.gifpt.file.domain.UploadFile;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface UploadedFileRepository extends JpaRepository<UploadFile, Long> {
    List<UploadFile> findByUserId(Long userId);
}
