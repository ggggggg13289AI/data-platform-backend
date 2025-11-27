# Frontend Development Guide

**Version**: v2.0.0  
**Last Updated**: 2025-11-07  
**Audience**: React/TypeScript developers working on Image Data Platform frontend

---

## 🎯 Quick Start for Frontend Developers

This guide helps you understand and extend the React frontend without needing to fully understand the backend.

---

## 📁 Frontend Project Structure

```
frontend/
├── src/
│   ├── components/              # Reusable UI components
│   │   ├── StudySearch/
│   │   │   ├── StudySearchForm.tsx
│   │   │   ├── StudyDetailModal.tsx
│   │   │   └── StudySearchForm.css
│   │   └── [other components]
│   │
│   ├── pages/                   # Full page components
│   │   ├── StudySearch.tsx      # Study search page
│   │   ├── StudySearch.css
│   │   └── [other pages]
│   │
│   ├── services/                # API client services
│   │   └── study.ts             # Study API calls
│   │
│   ├── hooks/                   # Custom React hooks
│   │   └── useStudySearch.ts    # Study search logic
│   │
│   ├── store/                   # Zustand state management
│   │   └── [store files]
│   │
│   ├── types/                   # TypeScript interfaces
│   │   └── study.ts             # Study-related types
│   │
│   ├── utils/                   # Utility functions
│   │   └── constants.ts         # App constants and routes
│   │
│   ├── assets/                  # Images, fonts, etc
│   │
│   └── App.tsx                  # Root component
│
├── package.json                 # Dependencies and scripts
├── vite.config.ts              # Vite build configuration
├── tsconfig.json               # TypeScript configuration
└── README.md                   # Project setup guide
```

---

## 🚀 Getting Started

### 1. Setup Development Environment

```bash
# Clone project
git clone https://github.com/your-org/image_data_platform.git
cd frontend

# Install dependencies
npm install  # or: pnpm install

# Start development server
npm run dev

# Access at http://localhost:3000
```

### 2. Configure API Base URL

**File**: `frontend/.env.local` (create if doesn't exist)

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

> **Note**: The `.env.local` file is git-ignored. Never commit API credentials.

### 3. Understand API Integration

All API calls go through **services**: `frontend/src/services/`

Example:
```typescript
// In component
import { studyService } from '../services/study';

// Make API call
const results = await studyService.searchStudies({
  q: 'search query',
  page: 1
});
```

---

## 🎨 Common Frontend Tasks

### Task 1: Adding a New Search Filter

**Goal**: Add ability to filter by equipment type

**Steps**:

#### 1a. Update Type Definition

**File**: `frontend/src/types/study.ts`

```typescript
// Add new field to SearchRequest
export interface StudySearchRequest {
  q?: string;
  exam_status?: string;
  exam_source?: string;
  exam_item?: string;
  equipment_type?: string;  // ← NEW
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}
```

#### 1b. Update API Service

**File**: `frontend/src/services/study.ts`

```typescript
async searchStudies(params: StudySearchRequest) {
  const response = await axiosInstance.get('/studies/search', {
    params: {
      ...params,
      // equipment_type will be automatically passed if present
    }
  });
  return response.data;
}
```

#### 1c. Update Search Form Component

**File**: `frontend/src/components/StudySearch/StudySearchForm.tsx`

```typescript
const StudySearchForm = ({ onSearch, filterOptions }) => {
  const [filters, setFilters] = useState({
    query: '',
    status: undefined,
    source: undefined,
    item: undefined,
    equipmentType: undefined,  // ← NEW
  });

  return (
    <Form>
      {/* ... existing filters ... */}
      
      <Form.Item label="Equipment Type">
        <Select
          placeholder="All Equipment Types"
          options={filterOptions?.equipment_types?.map(type => ({
            label: type,
            value: type
          }))}
          onChange={(value) => 
            setFilters({...filters, equipmentType: value})
          }
        />
      </Form.Item>
      
      <Button onClick={() => onSearch(filters)}>Search</Button>
    </Form>
  );
};
```

#### 1d. Update Parent Component

**File**: `frontend/src/pages/StudySearch.tsx`

```typescript
const handleSearch = async (filters) => {
  try {
    const results = await studyService.searchStudies({
      q: filters.query,
      exam_status: filters.status,
      exam_source: filters.source,
      exam_item: filters.item,
      equipment_type: filters.equipmentType,  // ← NEW
      page: currentPage
    });
    setSearchResults(results);
  } catch (error) {
    notification.error({ message: 'Search failed' });
  }
};
```

**That's it!** The new filter is now fully integrated.

---

### Task 2: Adding a New Modal for Viewing Details

**Goal**: Show study analysis results in a modal

**Steps**:

#### 2a. Create Type

**File**: `frontend/src/types/study.ts` (add to file)

```typescript
export interface AnalysisResult {
  id: string;
  exam_id: string;
  analysis_type: 'highlight' | 'classification' | 'extraction' | 'scoring';
  result: Record<string, any>;
  confidence: number;
  processing_time_ms: number;
  created_at: string;
}
```

#### 2b. Add API Method

**File**: `frontend/src/services/study.ts`

```typescript
async getAnalysis(examId: string): Promise<AnalysisResult[]> {
  const response = await axiosInstance.get(`/studies/${examId}/analysis`);
  return response.data;
}
```

#### 2c. Create Modal Component

**File**: `frontend/src/components/AnalysisModal.tsx`

```typescript
import { Modal, Spin, Empty, Badge, Statistic, Row, Col } from 'antd';

interface AnalysisModalProps {
  visible: boolean;
  examId: string;
  onClose: () => void;
}

export const AnalysisModal = ({ visible, examId, onClose }: AnalysisModalProps) => {
  const [loading, setLoading] = useState(false);
  const [analyses, setAnalyses] = useState<AnalysisResult[]>([]);

  useEffect(() => {
    if (visible) {
      loadAnalysis();
    }
  }, [visible, examId]);

  const loadAnalysis = async () => {
    setLoading(true);
    try {
      const data = await studyService.getAnalysis(examId);
      setAnalyses(data);
    } catch (error) {
      notification.error({ message: 'Failed to load analysis' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={`Analysis Results for ${examId}`}
      visible={visible}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <Spin spinning={loading}>
        {analyses.length === 0 ? (
          <Empty description="No analysis found" />
        ) : (
          <div>
            {analyses.map((analysis) => (
              <div key={analysis.id} style={{ marginBottom: 20 }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="Analysis Type"
                      value={analysis.analysis_type}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="Confidence"
                      value={(analysis.confidence * 100).toFixed(0)}
                      suffix="%"
                    />
                  </Col>
                </Row>
                <div style={{ marginTop: 12 }}>
                  <Badge status="success" text="Results:" />
                  <pre style={{ background: '#f5f5f5', padding: 12 }}>
                    {JSON.stringify(analysis.result, null, 2)}
                  </pre>
                </div>
              </div>
            ))}
          </div>
        )}
      </Spin>
    </Modal>
  );
};
```

#### 2d. Use Modal in Page

**File**: `frontend/src/pages/StudySearch.tsx`

```typescript
const [analysisModalVisible, setAnalysisModalVisible] = useState(false);
const [selectedExamId, setSelectedExamId] = useState<string | null>(null);

const handleViewAnalysis = (examId: string) => {
  setSelectedExamId(examId);
  setAnalysisModalVisible(true);
};

return (
  <>
    <Table
      columns={[
        // ... other columns
        {
          title: 'Actions',
          render: (_, record) => (
            <Button 
              type="link"
              onClick={() => handleViewAnalysis(record.exam_id)}
            >
              View Analysis
            </Button>
          )
        }
      ]}
      dataSource={searchResults}
    />
    
    <AnalysisModal
      visible={analysisModalVisible}
      examId={selectedExamId || ''}
      onClose={() => setAnalysisModalVisible(false)}
    />
  </>
);
```

---

## 🔌 API Service Pattern

All API calls follow this pattern:

```typescript
// File: frontend/src/services/[resource].ts
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add auth token to requests
axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const resourceService = {
  // GET single
  getOne: async (id: string) => {
    const response = await axiosInstance.get(`/resource/${id}`);
    return response.data;
  },

  // GET list
  getList: async (params?: any) => {
    const response = await axiosInstance.get('/resource', { params });
    return response.data;
  },

  // POST create
  create: async (data: any) => {
    const response = await axiosInstance.post('/resource', data);
    return response.data;
  },

  // PUT update
  update: async (id: string, data: any) => {
    const response = await axiosInstance.put(`/resource/${id}`, data);
    return response.data;
  },

  // DELETE
  delete: async (id: string) => {
    const response = await axiosInstance.delete(`/resource/${id}`);
    return response.data;
  }
};
```

---

## 🎣 Custom Hooks Pattern

Use custom hooks for repeated logic:

```typescript
// File: frontend/src/hooks/useApiCall.ts
import { useState, useCallback } from 'react';

export const useApiCall = <T,>(
  apiFunction: (...args: any[]) => Promise<T>
) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (...args: any[]) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFunction(...args);
      setData(result);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFunction]);

  return { data, loading, error, execute };
};

// Usage in component
const { data, loading, execute } = useApiCall(studyService.searchStudies);

const handleSearch = async () => {
  try {
    await execute({ q: 'search query' });
  } catch (err) {
    notification.error({ message: 'Search failed' });
  }
};
```

---

## 🎨 Component Structure Template

```typescript
// File: frontend/src/components/[ComponentName].tsx
import React, { useState, useEffect } from 'react';
import { [ImportFromAntDesign] } from 'antd';
import { [ImportService] } from '../services/[resource]';
import { [ImportTypes] } from '../types/[resource]';
import styles from './[ComponentName].module.css';

interface Props {
  // Component props
  [prop]: type;
}

export const [ComponentName] = ({ [prop] }: Props) => {
  // State
  const [data, setData] = useState<[Type][]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Effects
  useEffect(() => {
    loadData();
  }, []);

  // Methods
  const loadData = async () => {
    setLoading(true);
    try {
      const result = await [service].method();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading data');
    } finally {
      setLoading(false);
    }
  };

  // Render
  return (
    <div className={styles.container}>
      {loading ? (
        <Spin />
      ) : error ? (
        <Alert type="error" message={error} />
      ) : (
        // Component content
        <div>
          {/* JSX here */}
        </div>
      )}
    </div>
  );
};

export default [ComponentName];
```

---

## 🧪 Testing Frontend Components

### Setup Test File

**File**: `frontend/src/components/StudySearch/__tests__/StudySearchForm.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { StudySearchForm } from '../StudySearchForm';

describe('StudySearchForm', () => {
  const mockFilterOptions = {
    exam_statuses: ['completed', 'pending'],
    exam_sources: ['PAPA', 'Red'],
    exam_items: ['CT', 'MRI'],
    equipment_types: ['Device1', 'Device2']
  };

  it('renders search form', () => {
    const { container } = render(
      <StudySearchForm
        onSearch={jest.fn()}
        filterOptions={mockFilterOptions}
      />
    );
    expect(container).toBeInTheDocument();
  });

  it('calls onSearch with filters', async () => {
    const onSearch = jest.fn();
    render(
      <StudySearchForm
        onSearch={onSearch}
        filterOptions={mockFilterOptions}
      />
    );

    const searchButton = screen.getByText('Search');
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(onSearch).toHaveBeenCalled();
    });
  });
});
```

---

## 🐛 Debugging Tips

### 1. Check API Calls

Open browser DevTools → Network tab:
- Look for `/api/v1/studies/search` requests
- Check Response tab for API response
- Check status code (should be 200)

### 2. Check Frontend State

In browser console:
```javascript
// If using Zustand store
// (Replace with your actual store name)
import { useStudyStore } from './store/study';
const store = useStudyStore.getState();
console.log(store); // See current state
```

### 3. Check Backend Logs

```bash
# If running backend in terminal
# Look for error messages:
# - "404 Not Found"
# - "500 Internal Server Error"
# - Connection refused (backend not running)

# If using Docker:
docker-compose logs backend  # See backend logs
docker-compose logs  # See all service logs
```

### 4. API Response Format

When backend response doesn't match expected format:

```typescript
// Add debugging
const response = await studyService.searchStudies(params);
console.log('API Response:', response);  // ← See actual response
console.log('Expected Type:', response.data);  // ← Should be array
```

---

## 📚 Key Files Reference

| File | Purpose |
|------|---------|
| `frontend/src/services/study.ts` | All study API calls |
| `frontend/src/types/study.ts` | Study-related types |
| `frontend/src/pages/StudySearch.tsx` | Study search page |
| `frontend/src/hooks/useStudySearch.ts` | Study search logic |
| `frontend/src/utils/constants.ts` | App routes and config |
| `frontend/.env.local` | Local environment (git-ignored) |
| `frontend/package.json` | Dependencies |
| `frontend/vite.config.ts` | Build configuration |

---

## 🔄 Workflow for New Features

1. **Read** related documentation
2. **Plan** component structure
3. **Add** TypeScript types
4. **Create** service method if needed
5. **Build** component(s)
6. **Test** locally (npm run dev)
7. **Debug** using browser DevTools
8. **Submit** pull request

---

## 📞 Common Questions

### Q: How do I make an API call?

```typescript
import { studyService } from '../services/study';

const results = await studyService.searchStudies({
  q: 'search term',
  page: 1
});
```

### Q: How do I show a loading indicator?

```typescript
const [loading, setLoading] = useState(false);

const handleClick = async () => {
  setLoading(true);
  try {
    await someAsyncOperation();
  } finally {
    setLoading(false);
  }
};

return <Spin spinning={loading}>{/* content */}</Spin>;
```

### Q: How do I show an error message?

```typescript
import { notification } from 'antd';

try {
  // API call
} catch (error) {
  notification.error({
    message: 'Operation failed',
    description: error.message
  });
}
```

### Q: How do I add a new route?

```typescript
// frontend/src/utils/constants.ts
export const ROUTES = {
  // ... existing routes
  NEW_PAGE: '/new-page'
};

// frontend/src/App.tsx
<Routes>
  {/* ... existing routes */}
  <Route path={ROUTES.NEW_PAGE} element={<NewPage />} />
</Routes>

// frontend/src/pages/NewPage.tsx
export const NewPage = () => {
  return <div>New page content</div>;
};
```

---

## 🎓 Learning Resources

### For React
- [React Hooks Documentation](https://react.dev/reference/react)
- [React TypeScript Guide](https://react-typescript-cheatsheet.netlify.app/)

### For Ant Design
- [Ant Design Component Library](https://ant.design/components/overview/)
- [Form Component](https://ant.design/components/form/)
- [Table Component](https://ant.design/components/table/)

### For Zustand
- [Zustand Documentation](https://github.com/pmndrs/zustand)

### For Testing
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)

---

## 📝 Code Style Guide

### TypeScript
```typescript
// ✅ Use types, not interfaces for objects
type Study = {
  id: string;
  name: string;
};

// ✅ Use const for functions
const handleSearch = (query: string) => { };

// ✅ Use arrow functions in JSX
<Button onClick={() => handleClick()}>Click</Button>

// ❌ Avoid using any
const data: any = response.data;  // BAD

// ✅ Use proper typing
const data: StudyListItem[] = response.data;  // GOOD
```

### React
```typescript
// ✅ Use functional components
export const MyComponent = () => {};

// ✅ Use custom hooks for logic
const { data, loading } = useStudySearch();

// ✅ Keep components small and focused
// Each component should do one thing

// ❌ Avoid large components
// If component is >200 lines, split it
```

---

**Document Version**: v2.0.0  
**Last Updated**: 2025-11-07  
**Maintained By**: Image Data Platform Team
