# Edge Cases Handling Documentation

## Overview

This document details all edge cases handled by the ATC Conflict Generation System web interface. The system implements comprehensive error handling, validation, and recovery mechanisms to ensure robust operation under various failure conditions.

## File Upload Edge Cases

### 1. Network and Connectivity Issues

**Edge Case**: Network timeout during file upload
- **Detection**: 30-second timeout on upload requests
- **Handling**: AbortController with timeout
- **User Feedback**: Clear error message with retry guidance
- **Recovery**: Automatic retry with exponential backoff

**Edge Case**: Network disconnection
- **Detection**: Fetch API error handling
- **Handling**: Graceful error display with network-specific messages
- **User Feedback**: "Network error. Please check your connection."
- **Recovery**: Manual retry by user

### 2. File Validation Edge Cases

**Edge Case**: Empty files
- **Detection**: File size check (0 bytes)
- **Handling**: Skip empty files with warning
- **User Feedback**: "Empty file skipped: filename"
- **Recovery**: User can upload valid files

**Edge Case**: Non-XML files
- **Detection**: File extension and MIME type validation
- **Handling**: Filter out non-XML files
- **User Feedback**: "Skipping non-XML file: filename"
- **Recovery**: User can select valid XML files

**Edge Case**: Oversized files
- **Detection**: File size > 16MB limit
- **Handling**: Reject upload with size information
- **User Feedback**: "File too large: filename (size)"
- **Recovery**: User can compress or split files

**Edge Case**: Duplicate filenames
- **Detection**: Check for existing files with same name
- **Handling**: Auto-rename with counter (file_1.xml, file_2.xml)
- **User Feedback**: "Renamed duplicate file to: new_filename"
- **Recovery**: Automatic, no user action required

### 3. File Content Edge Cases

**Edge Case**: Malformed XML
- **Detection**: XML parsing during validation
- **Handling**: Mark as invalid with specific error
- **User Feedback**: "File validation failed: parsing error"
- **Recovery**: User must fix XML structure

**Edge Case**: Unicode encoding issues
- **Detection**: UTF-8 decode errors
- **Handling**: Graceful error with encoding information
- **User Feedback**: "File contains invalid characters"
- **Recovery**: User must save file with proper encoding

**Edge Case**: Files too large for validation
- **Detection**: File size > 50MB for validation
- **Handling**: Skip validation with size warning
- **User Feedback**: "File too large for validation (max 50MB)"
- **Recovery**: User can process without validation

**Edge Case**: Duplicate Origin-Destination Routes

- The system cannot process multiple flights with the same origin and destination.
- Only the first flight per route will be processed.
- **To avoid this limitation:** Remove duplicate files with the same origin and destination.

## Processing Edge Cases

### 1. System Resource Issues

**Edge Case**: Insufficient disk space
- **Detection**: Disk space check before upload/processing
- **Handling**: Reject operation with space information
- **User Feedback**: "Insufficient disk space on server"
- **Recovery**: Admin must free up space

**Edge Case**: High memory usage
- **Detection**: Memory usage monitoring
- **Handling**: Reject operations when memory > 90%
- **User Feedback**: "Server is under high load. Please try again later."
- **Recovery**: Wait for memory to free up

**Edge Case**: Processing timeout
- **Detection**: 5-minute timeout per processing step
- **Handling**: Kill process and cleanup
- **User Feedback**: "Processing timed out after 5 minutes"
- **Recovery**: Retry with fewer files

### 2. Processing Validation Edge Cases

**Edge Case**: Invalid files selected for processing
- **Detection**: Pre-processing validation check
- **Handling**: Block processing with file list
- **User Feedback**: "Cannot process invalid files: file1, file2"
- **Recovery**: User must select valid files

**Edge Case**: Too many files selected
- **Detection**: File count > 100 limit
- **Handling**: Reject processing request
- **User Feedback**: "Too many files selected (max 100)"
- **Recovery**: User must select fewer files

**Edge Case**: Large files selected
- **Detection**: Individual file size > 10MB
- **Handling**: Warn user about processing time
- **User Feedback**: "Large files detected. Processing may take longer."
- **Recovery**: User can proceed or select smaller files

### 3. Processing Execution Edge Cases

**Edge Case**: Subprocess failures
- **Detection**: Subprocess return codes and exceptions
- **Handling**: Stop processing and cleanup
- **User Feedback**: "Processing failed at step X: error details"
- **Recovery**: Automatic cleanup, manual retry

**Edge Case**: Missing source files
- **Detection**: File existence check before copying
- **Handling**: Stop processing with file list
- **User Feedback**: "Source file not found: filename"
- **Recovery**: Re-upload missing files

**Edge Case**: File permission issues
- **Detection**: OS-level file operation errors
- **Handling**: Graceful error with permission details
- **User Feedback**: "Permission denied accessing file"
- **Recovery**: Check file permissions

## Frontend Edge Cases

### 1. UI State Management

**Edge Case**: Multiple simultaneous uploads
- **Detection**: Upload state tracking
- **Handling**: Queue uploads and show progress
- **User Feedback**: "Uploading X files..."
- **Recovery**: Automatic queue processing

**Edge Case**: Processing already in progress
- **Detection**: Processing state check
- **Handling**: Block new processing requests
- **User Feedback**: "Processing already in progress. Please wait."
- **Recovery**: Wait for current processing to complete

**Edge Case**: Browser refresh during processing
- **Detection**: Page unload events
- **Handling**: Warn user about data loss
- **User Feedback**: "Processing in progress. Are you sure you want to leave?"
- **Recovery**: User can cancel or proceed

### 2. Data Validation Edge Cases

**Edge Case**: Validation retry failures
- **Detection**: Multiple validation attempts
- **Handling**: Exponential backoff with max retries
- **User Feedback**: "File validation failed after 3 attempts"
- **Recovery**: Manual retry or skip validation

**Edge Case**: Cached validation data
- **Detection**: Validation cache with timestamps
- **Handling**: Show cached results with warning
- **User Feedback**: "Showing cached file list. Some files may not be up to date."
- **Recovery**: Refresh to get latest data

### 3. User Interaction Edge Cases

**Edge Case**: Files with no flights
- **Detection**: Flight count validation
- **Handling**: Warn user with confirmation
- **User Feedback**: "Warning: Files with no flights detected. Continue?"
- **Recovery**: User can proceed or cancel

**Edge Case**: Large file warnings
- **Detection**: File size thresholds
- **Handling**: Confirm with user before processing
- **User Feedback**: "Large files detected. Processing may take longer. Continue?"
- **Recovery**: User can proceed or select smaller files

## Backend Edge Cases

### 1. Server Resource Management

**Edge Case**: Disk space monitoring
- **Detection**: Real-time disk space checks
- **Handling**: Reject operations when space < 1GB
- **User Feedback**: "Insufficient disk space"
- **Recovery**: Admin intervention required

**Edge Case**: Memory usage monitoring
- **Detection**: System memory percentage
- **Handling**: Reject operations when memory > 90%
- **User Feedback**: "Server under high load"
- **Recovery**: Wait for memory to free up

### 2. File System Edge Cases

**Edge Case**: Directory access issues
- **Detection**: OS-level directory operations
- **Handling**: Graceful error with directory info
- **User Feedback**: "Could not read file directory"
- **Recovery**: Check directory permissions

**Edge Case**: File corruption
- **Detection**: File read/write operations
- **Handling**: Skip corrupted files with error
- **User Feedback**: "Could not read file: filename"
- **Recovery**: Re-upload file

### 3. Process Management Edge Cases

**Edge Case**: Subprocess timeouts
- **Detection**: Timeout parameters on subprocess calls
- **Handling**: Kill process and cleanup
- **User Feedback**: "Processing timed out at step X"
- **Recovery**: Retry with fewer files

**Edge Case**: Subprocess crashes
- **Detection**: Subprocess return codes
- **Handling**: Stop processing and cleanup
- **User Feedback**: "Processing failed at step X: error"
- **Recovery**: Automatic cleanup, manual retry

## Error Recovery Mechanisms

### 1. Automatic Recovery

**File Upload Recovery**:
- Retry failed uploads with exponential backoff
- Auto-rename duplicate files
- Skip invalid files with warnings

**Processing Recovery**:
- Automatic cleanup on failure
- Restore original working directory
- Remove temporary files

**Validation Recovery**:
- Retry validation with backoff
- Cache validation results
- Graceful degradation for large files

### 2. Manual Recovery

**User-Initiated Recovery**:
- Retry processing button
- Re-upload failed files
- Refresh file library

**Admin Recovery**:
- Clear disk space
- Restart server
- Check file permissions

## Monitoring and Logging

### 1. Error Tracking

**Structured Logging**:
- All errors logged with timestamps
- Error severity levels (INFO, WARNING, ERROR)
- File and line number information

**User Feedback**:
- Clear, actionable error messages
- Specific guidance for recovery
- Progress indicators for long operations

### 2. Performance Monitoring

**Resource Monitoring**:
- Disk space usage
- Memory usage
- Processing time tracking

**Operation Tracking**:
- Upload success/failure rates
- Processing step completion times
- Validation success rates

## Testing Edge Cases

### 1. Automated Testing

**File Upload Tests**:
- Empty files
- Oversized files
- Malformed XML
- Duplicate filenames

**Processing Tests**:
- Timeout scenarios
- Resource exhaustion
- Subprocess failures
- File permission issues

### 2. Manual Testing

**User Scenarios**:
- Network disconnection during upload
- Browser refresh during processing
- Large file processing
- Multiple simultaneous operations

## Configuration for Edge Cases

### 1. Timeout Settings

```python
# File upload timeout
UPLOAD_TIMEOUT = 30000  # 30 seconds

# Processing step timeouts
EXTRACT_TIMEOUT = 300   # 5 minutes
CONFLICT_TIMEOUT = 600  # 10 minutes
MERGE_TIMEOUT = 300     # 5 minutes
SCHEDULE_TIMEOUT = 300  # 5 minutes
ANIMATION_TIMEOUT = 300 # 5 minutes
AUDIT_TIMEOUT = 300     # 5 minutes
```

### 2. Resource Limits

```python
# File size limits
MAX_UPLOAD_SIZE = 16 * 1024 * 1024  # 16MB
MAX_VALIDATION_SIZE = 50 * 1024 * 1024  # 50MB
MAX_PROCESSING_SIZE = 10 * 1024 * 1024  # 10MB

# Count limits
MAX_FILES_PER_UPLOAD = 50
MAX_FILES_PER_PROCESS = 100

# Resource thresholds
MIN_DISK_SPACE_GB = 1
MAX_MEMORY_PERCENT = 90
```

### 3. Retry Settings

```python
# Validation retries
MAX_VALIDATION_RETRIES = 3
VALIDATION_RETRY_DELAY = 1000  # 1 second

# Processing retries
MAX_PROCESSING_RETRIES = 3
PROCESSING_RETRY_DELAY = 2000  # 2 seconds
```

## Best Practices

### 1. User Experience

- Always provide clear, actionable error messages
- Show progress indicators for long operations
- Allow users to retry failed operations
- Gracefully handle network issues

### 2. System Reliability

- Implement comprehensive logging
- Monitor system resources
- Clean up temporary files
- Handle all possible failure modes

### 3. Performance

- Use timeouts to prevent hanging operations
- Implement caching for repeated operations
- Monitor and log performance metrics
- Optimize for common failure scenarios

## Conclusion

The web interface implements comprehensive edge case handling to ensure robust operation under various failure conditions. The system provides clear user feedback, automatic recovery mechanisms, and detailed logging for troubleshooting. This approach ensures a reliable user experience while maintaining system stability and performance. 