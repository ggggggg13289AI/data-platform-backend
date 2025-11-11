# Backend Integration Checklist

When integrating the real backend with the Study Search frontend, follow this checklist.

## API Endpoint Requirements

### 1. Search Studies Endpoint
**Method**: `GET /api/v1/studies/search`

**Query Parameters**:
```
q: string (required) - Search query
exam_status?: string - Filter by status
exam_source?: string - Filter by source
exam_item?: string - Filter by exam item
start_date?: string (YYYY-MM-DD) - Filter by start date
end_date?: string (YYYY-MM-DD) - Filter by end date
page?: number (default: 1) - Page number
page_size?: number (default: 20) - Results per page
sort?: string (default: 'order_datetime_desc') - Sort option
```

**Response Format** (REQUIRED):
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "studies": [
      {
        "exam_id": "EXAM000001",
        "medical_record_no": "MR00000001",
        "application_order_no": "AON000001",
        "patient_name": "John Doe",
        "patient_gender": "M",
        "patient_age": 45,
        "exam_status": "Completed",
        "exam_source": "PACS",
        "exam_item": "CT",
        "exam_description": "CT scan of chest",
        "order_datetime": "2024-11-07T14:30:00Z",
        "check_in_datetime": "2024-11-07T14:15:00Z",
        "report_certification_datetime": "2024-11-07T15:00:00Z",
        "certified_physician": "Dr. Smith"
      }
    ]
  }
}
```

**Key Requirements**:
- ✅ Wrap response in `code`, `message`, `data` structure
- ✅ Field names must match exactly (case-sensitive)
- ✅ `studies` array must be in `data` object
- ✅ All datetime fields should be ISO 8601 format
- ✅ Support pagination with `page` and `page_size`
- ✅ Return `total` count for pagination display

### 2. Filter Options Endpoint
**Method**: `GET /api/v1/studies/filters/options`

**Query Parameters**: None

**Response Format** (REQUIRED):
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "exam_statuses": [
      "Completed",
      "In Progress",
      "Pending Review",
      "Cancelled"
    ],
    "exam_sources": [
      "HIS",
      "PACS",
      "RIS",
      "LIS"
    ],
    "exam_items": [
      "CT",
      "MRI",
      "X-Ray",
      "Ultrasound",
      "PET"
    ],
    "equipment_types": [
      "Equipment 1",
      "Equipment 2",
      "Equipment 3"
    ]
  }
}
```

**Key Requirements**:
- ✅ Return arrays of unique values for each filter type
- ✅ No leading "All" option needed - frontend adds it
- ✅ Use standard medical abbreviations
- ✅ Cached on frontend after first load

### 3. Study Detail Endpoint
**Method**: `GET /api/v1/studies/{exam_id}`

**Path Parameters**:
- `exam_id`: The exam ID (e.g., "EXAM000001")

**Response Format** (REQUIRED):
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "exam_id": "EXAM000001",
    "medical_record_no": "MR00000001",
    "application_order_no": "AON000001",
    "patient_name": "John Doe",
    "patient_gender": "M",
    "patient_birth_date": "1979-05-15",
    "patient_age": 45,
    "exam_status": "Completed",
    "exam_source": "PACS",
    "exam_room": "Room 101",
    "exam_item": "CT",
    "exam_description": "CT scan of chest",
    "exam_equipment": "Siemens SOMATOM",
    "equipment_type": "CT Scanner",
    "order_datetime": "2024-11-07T14:30:00Z",
    "check_in_datetime": "2024-11-07T14:15:00Z",
    "report_certification_datetime": "2024-11-07T15:00:00Z",
    "certified_physician": "Dr. Smith",
    "data_load_time": "2024-11-07T15:05:00Z"
  }
}
```

**Key Requirements**:
- ✅ All fields optional except `exam_id`, `patient_name`
- ✅ Match field names from Study interface
- ✅ Include full details not shown in list view
- ✅ ISO 8601 datetime format

### 4. Export Studies Endpoint
**Method**: `GET /api/v1/studies/export`

**Query Parameters**: (Same as search endpoint)
```
q, exam_status, exam_source, exam_item, start_date, end_date
```

**Response**:
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Binary Excel file data
- Suggested filename: `studies_export_TIMESTAMP.xlsx`

## Testing Checklist

Before deploying backend:

### API Endpoint Tests
- [ ] Search endpoint returns correct data structure
- [ ] Field names match exactly (case-sensitive)
- [ ] Pagination works (test different pages)
- [ ] Filter options endpoint returns all dropdown values
- [ ] Study detail endpoint returns complete information
- [ ] Datetime fields are ISO 8601 format
- [ ] Total count is accurate

### Frontend Integration Tests
- [ ] Search form submits without errors
- [ ] Results display in table
- [ ] Pagination works (navigate between pages)
- [ ] Filter dropdowns populate correctly
- [ ] View Details button opens modal
- [ ] Modal displays all study information
- [ ] Export button downloads Excel file
- [ ] Clear button resets form

### Error Handling Tests
- [ ] Search with empty query shows error
- [ ] Search with no results shows "No studies found"
- [ ] API error displays error message to user
- [ ] Network timeout handles gracefully

## Common Issues & Solutions

### Issue: Field Names Don't Match
**Error**: Table shows empty values or "undefined"
**Solution**: 
- Check response field names are exactly: `exam_id`, `patient_name`, `medical_record_no`, etc.
- JavaScript is case-sensitive: `exam_ID` ≠ `exam_id`
- Use the field list from `StudyListItem` type definition

### Issue: No Results Despite Query
**Error**: Search returns empty array
**Solution**:
- Verify search query matches database values
- Check if filters are excluding all results
- Ensure `total` count is accurate

### Issue: Pagination Broken
**Error**: Clicking next page doesn't change results
**Solution**:
- Verify `page` parameter is being sent to backend
- Ensure `total_pages` is calculated correctly: `ceil(total / page_size)`
- Check if `page_size` is respected

### Issue: Filter Dropdowns Empty
**Error**: Dropdowns show only placeholder
**Solution**:
- Verify `/filters/options` endpoint returns non-empty arrays
- Check for typos in response field names
- Ensure `code: 200` in response

### Issue: Detail Modal Shows Empty
**Error**: Modal opens but shows no data
**Solution**:
- Verify `{exam_id}` path parameter is correctly formatted
- Check all required fields are in Study response
- Ensure datetime formatting is consistent

## Performance Recommendations

1. **Search Endpoint**:
   - Use database indexes on: `q`, `exam_status`, `exam_source`, `exam_item`
   - Consider full-text search for patient name/description
   - Implement result limit on `page_size` (recommend max 100)

2. **Filter Options**:
   - Cache response (data changes infrequently)
   - Consider invalidating cache on data updates
   - Return deduplicated, sorted values

3. **Study Detail**:
   - Use indexed lookups by `exam_id`
   - Consider lazy loading for large image/document fields
   - Cache frequently accessed studies

## Security Considerations

1. **Authentication**:
   - API client includes `Authorization: Bearer {token}` header
   - Frontend handles 401 Unauthorized (redirects to login)
   - Verify backend validates token on all endpoints

2. **Data Validation**:
   - Validate search query length (recommend max 255 chars)
   - Validate page number is positive integer
   - Sanitize all string inputs

3. **Access Control**:
   - Verify user has permission to access studies
   - Implement row-level security if needed
   - Filter results by user's organization/department

4. **Rate Limiting**:
   - Implement rate limiting on search endpoint
   - Suggest: 100 requests per minute per user
   - Return 429 Too Many Requests if exceeded

## Deployment Steps

1. **Prepare Backend**:
   - [ ] Implement all 4 API endpoints
   - [ ] Test endpoints with Postman/curl
   - [ ] Verify response format matches specification

2. **Update Frontend Configuration** (if needed):
   - [ ] Check `API_CONFIG.BASE_URL` in `frontend/src/utils/constants.ts`
   - [ ] Update to production API URL if different

3. **Testing**:
   - [ ] Run manual tests from "Testing Checklist" above
   - [ ] Test with real data in database
   - [ ] Verify all search scenarios work

4. **Disable Mock API** (optional):
   - [ ] Remove `enableMockApiInterceptor(apiClient)` from `api.ts` if needed
   - [ ] Or keep it for fallback (recommended)

5. **Monitor**:
   - [ ] Check browser console for errors
   - [ ] Monitor API response times
   - [ ] Track user feedback on search functionality

## Support

If issues occur during integration:

1. **Check API Response Format**:
   - Open browser DevTools → Network tab
   - Click on API request
   - Verify Response matches specification

2. **Check Browser Console**:
   - DevTools → Console tab
   - Look for error messages
   - Verify mock API is disabled if using real API

3. **Verify Field Names**:
   - Compare actual response with `StudyListItem` type
   - Ensure exact match (case-sensitive)

4. **Test API Directly**:
   ```bash
   curl -H "Authorization: Bearer {token}" \
        "http://localhost:8000/api/v1/studies/search?q=test&page=1&page_size=20"
   ```

## Contact

For questions about the frontend implementation or integration:
- See `docs/guides/STUDY_SEARCH_IMPLEMENTATION.md` for detailed documentation
- Check `frontend/src/types/study.ts` for TypeScript type definitions
- Review `frontend/src/services/study.ts` for API client implementation
