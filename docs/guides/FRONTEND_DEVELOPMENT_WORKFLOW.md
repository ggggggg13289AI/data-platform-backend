# 前端开发工作流 - Phase 1

**版本**: v1.0.0
**创建日期**: 2025-11-06
**项目**: 影像数据平台 - AI辅助报告筛选系统
**技术栈**: React 18 + TypeScript + Ant Design + Zustand + Vite

---

## 📋 目录

1. [前端架构总览](#前端架构总览)
2. [开发环境准备](#开发环境准备)
3. [项目初始化工作流](#项目初始化工作流)
4. [核心功能开发顺序](#核心功能开发顺序)
5. [组件开发规范](#组件开发规范)
6. [状态管理策略](#状态管理策略)
7. [API集成方案](#api集成方案)
8. [路由设计](#路由设计)
9. [测试策略](#测试策略)
10. [性能优化](#性能优化)
11. [部署流程](#部署流程)

---

## 前端架构总览

### 技术选型理由

| 技术 | 版本 | 选择理由 |
|-----|------|---------|
| **React** | 18.2+ | 成熟生态系统、丰富组件库、优秀开发体验 |
| **TypeScript** | 5.0+ | 类型安全、代码提示、减少运行时错误 |
| **Ant Design** | 5.x | 企业级UI设计语言、丰富组件、中文友好 |
| **Zustand** | 4.x | 轻量级状态管理、简单API、无模板代码 |
| **Vite** | 5.x | 极速开发服务器、原生ESM、优化的构建输出 |
| **React Router** | 6.x | 标准路由库、声明式导航、嵌套路由 |
| **Axios** | 1.x | Promise-based HTTP、请求拦截、错误处理 |

### Phase 1 前端页面结构

```
Frontend Application
├── 🔐 Login Page (登录页)
├── 📊 Dashboard (仪表盘)
│   ├── 数据统计概览
│   ├── 最近导入记录
│   └── AI分析任务状态
├── 📂 Data Import (数据导入)
│   ├── 文件上传
│   ├── 字段映射
│   ├── 数据预览
│   └── 导入确认
├── 🔍 Report Search (报告检索)
│   ├── 全文搜索
│   ├── 高级筛选
│   ├── 报告列表
│   └── 报告详情
├── 🤖 AI Analysis (AI分析)
│   ├── 单报告分析
│   ├── 批量分析
│   ├── 提示词管理
│   └── 分析结果查看
├── 📁 Projects (项目管理)
│   ├── 项目列表
│   ├── 项目详情
│   ├── 报告关联
│   └── 导出功能
└── ⚙️ Settings (设置)
    ├── 个人资料
    └── 密码修改
```

### 组件层级架构

```
src/
├── components/              # 可复用组件
│   ├── Layout/             # 布局组件
│   │   ├── MainLayout.tsx
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   ├── Common/             # 通用组件
│   │   ├── Loading.tsx
│   │   ├── ErrorBoundary.tsx
│   │   └── ProtectedRoute.tsx
│   ├── Report/             # 报告相关组件
│   │   ├── ReportTable.tsx
│   │   ├── ReportCard.tsx
│   │   ├── ReportDetail.tsx
│   │   └── SearchFilters.tsx
│   ├── AIAnalysis/         # AI分析组件
│   │   ├── AnalysisForm.tsx
│   │   ├── AnnotationViewer.tsx
│   │   ├── PromptLibrary.tsx
│   │   └── BatchAnalysisStatus.tsx
│   └── Project/            # 项目管理组件
│       ├── ProjectList.tsx
│       ├── ProjectCard.tsx
│       └── ReportSelector.tsx
├── pages/                  # 页面组件
│   ├── Login/
│   ├── Dashboard/
│   ├── DataImport/
│   ├── ReportSearch/
│   ├── AIAnalysis/
│   ├── Projects/
│   └── Settings/
├── services/               # API服务层
│   ├── api.ts             # Axios配置
│   ├── auth.ts            # 认证API
│   ├── reports.ts         # 报告API
│   ├── aiAnalysis.ts      # AI分析API
│   └── projects.ts        # 项目API
├── store/                  # Zustand状态管理
│   ├── authStore.ts       # 认证状态
│   ├── reportStore.ts     # 报告状态
│   └── appStore.ts        # 全局应用状态
├── types/                  # TypeScript类型定义
│   ├── report.ts
│   ├── project.ts
│   ├── aiAnnotation.ts
│   └── user.ts
├── utils/                  # 工具函数
│   ├── formatters.ts      # 格式化工具
│   ├── validators.ts      # 验证函数
│   └── constants.ts       # 常量定义
├── hooks/                  # 自定义Hooks
│   ├── useAuth.ts
│   ├── useDebounce.ts
│   └── usePagination.ts
├── App.tsx                 # 根组件
├── main.tsx                # 应用入口
└── vite.config.ts          # Vite配置
```

---

## 开发环境准备

### 前置要求

- **Node.js**: 18.x 或 20.x LTS
- **npm**: 9.x+ 或 **pnpm**: 8.x+ (推荐)
- **VS Code**: 推荐IDE
- **VS Code扩展**:
  - ESLint
  - Prettier
  - TypeScript Vue Plugin (Volar)
  - ES7+ React/Redux/React-Native snippets

### 环境验证

```bash
# 验证Node.js版本
node --version  # 应该显示 v18.x 或 v20.x

# 验证npm版本
npm --version   # 应该显示 9.x+

# 安装pnpm (可选，推荐)
npm install -g pnpm

# 验证pnpm
pnpm --version  # 应该显示 8.x+
```

---

## 项目初始化工作流

### Phase 1.1: 创建React项目 (Day 1 - 2小时)

**目标**: 使用Vite创建TypeScript + React项目骨架

```bash
# 1. 创建项目目录
cd D:\00_Chen\spider\image_data_platform
mkdir frontend
cd frontend

# 2. 使用Vite创建React + TypeScript项目
pnpm create vite . --template react-ts

# 3. 安装依赖
pnpm install

# 4. 验证项目运行
pnpm dev  # 访问 http://localhost:5173

# 5. 初始化Git（如果未初始化）
git init
git add .
git commit -m "chore: initialize React + TypeScript project with Vite"
```

**验收标准**:
- ✅ Vite开发服务器正常启动
- ✅ 浏览器显示默认Vite + React页面
- ✅ TypeScript编译无错误
- ✅ 项目提交到Git

### Phase 1.2: 安装核心依赖 (Day 1 - 1小时)

```bash
# UI组件库
pnpm add antd

# 路由
pnpm add react-router-dom

# 状态管理
pnpm add zustand

# HTTP客户端
pnpm add axios

# 工具库
pnpm add dayjs  # 日期处理
pnpm add lodash-es  # 工具函数库

# 类型定义
pnpm add -D @types/lodash-es
```

**依赖清单验证** (`package.json`):
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "antd": "^5.12.0",
    "zustand": "^4.4.7",
    "axios": "^1.6.2",
    "dayjs": "^1.11.10",
    "lodash-es": "^4.17.21"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@types/lodash-es": "^4.17.12",
    "@typescript-eslint/eslint-plugin": "^6.14.0",
    "@typescript-eslint/parser": "^6.14.0",
    "@vitejs/plugin-react": "^4.2.1",
    "eslint": "^8.55.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
```

### Phase 1.3: 项目配置 (Day 1 - 2小时)

#### 1. 配置Vite (`vite.config.ts`)

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@services': path.resolve(__dirname, './src/services'),
      '@store': path.resolve(__dirname, './src/store'),
      '@types': path.resolve(__dirname, './src/types'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

#### 2. 配置TypeScript (`tsconfig.json`)

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@pages/*": ["./src/pages/*"],
      "@services/*": ["./src/services/*"],
      "@store/*": ["./src/store/*"],
      "@types/*": ["./src/types/*"],
      "@utils/*": ["./src/utils/*"],
      "@hooks/*": ["./src/hooks/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

#### 3. 配置ESLint (`.eslintrc.cjs`)

```javascript
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'warn',
  },
}
```

#### 4. 配置Prettier (`.prettierrc`)

```json
{
  "semi": false,
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "trailingComma": "es5",
  "arrowParens": "avoid"
}
```

#### 5. 创建环境变量配置

`.env.development`:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=影像数据平台 - AI辅助报告筛选系统
```

`.env.production`:
```env
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1
VITE_APP_TITLE=影像数据平台
```

**验收标准**:
- ✅ TypeScript路径别名正常工作
- ✅ ESLint检查无错误
- ✅ 开发服务器代理到后端API正常
- ✅ 环境变量正确读取

### Phase 1.4: 创建基础目录结构 (Day 1 - 30分钟)

```bash
cd src

# 创建目录结构
mkdir -p components/{Layout,Common,Report,AIAnalysis,Project}
mkdir -p pages/{Login,Dashboard,DataImport,ReportSearch,AIAnalysis,Projects,Settings}
mkdir -p services
mkdir -p store
mkdir -p types
mkdir -p utils
mkdir -p hooks
mkdir -p assets/{images,styles}

# 创建空的index文件
touch components/index.ts
touch pages/index.ts
touch services/index.ts
touch store/index.ts
touch types/index.ts
touch utils/index.ts
touch hooks/index.ts
```

**最终目录结构验证**:
```
src/
├── assets/
│   ├── images/
│   └── styles/
│       └── global.css
├── components/
│   ├── Layout/
│   ├── Common/
│   ├── Report/
│   ├── AIAnalysis/
│   ├── Project/
│   └── index.ts
├── pages/
│   ├── Login/
│   ├── Dashboard/
│   ├── DataImport/
│   ├── ReportSearch/
│   ├── AIAnalysis/
│   ├── Projects/
│   ├── Settings/
│   └── index.ts
├── services/
│   └── index.ts
├── store/
│   └── index.ts
├── types/
│   └── index.ts
├── utils/
│   └── index.ts
├── hooks/
│   └── index.ts
├── App.tsx
├── main.tsx
└── vite-env.d.ts
```

---

## 核心功能开发顺序

### 🎯 开发优先级矩阵

| 优先级 | 功能模块 | 开发周期 | 依赖关系 |
|-------|---------|---------|---------|
| **P0 - 关键路径** | 认证系统 | Day 2 | 无 |
| **P0** | 布局框架 | Day 2 | 认证系统 |
| **P1 - 核心功能** | 数据导入 | Day 3-4 | 布局框架 |
| **P1** | 报告检索 | Day 5-6 | 布局框架 |
| **P1** | AI分析 | Day 7-9 | 报告检索 |
| **P2 - 辅助功能** | 项目管理 | Day 10-11 | 报告检索 |
| **P2** | 仪表盘 | Day 12 | 所有核心功能 |
| **P3 - 优化** | 设置页面 | Day 13 | 认证系统 |

---

## Phase 2: 认证系统开发 (Day 2 - 1天)

### 2.1 类型定义 (`src/types/user.ts`)

```typescript
// 用户角色
export type UserRole = 'admin' | 'researcher' | 'viewer'

// 用户信息接口
export interface User {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

// 登录请求
export interface LoginRequest {
  username: string  // 实际是email
  password: string
}

// 登录响应
export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

// 认证状态
export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => void
  checkAuth: () => void
}
```

### 2.2 Axios配置 (`src/services/api.ts`)

```typescript
import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
import { message } from 'antd'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// 创建Axios实例
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加token
apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  response => response.data,
  (error: AxiosError) => {
    // 处理401未授权
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
      message.error('登录已过期，请重新登录')
    }

    // 处理其他错误
    const errorMessage = (error.response?.data as any)?.detail || '请求失败，请稍后重试'
    message.error(errorMessage)

    return Promise.reject(error)
  }
)

export default apiClient
```

### 2.3 认证API (`src/services/auth.ts`)

```typescript
import apiClient from './api'
import { LoginRequest, LoginResponse, User } from '@types/user'

export const authApi = {
  // 登录
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // FastAPI OAuth2PasswordBearer需要表单格式
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response
  },

  // 获取当前用户信息
  async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/auth/me')
  },

  // 登出
  async logout(): Promise<void> {
    return apiClient.post('/auth/logout')
  },
}
```

### 2.4 认证状态管理 (`src/store/authStore.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { AuthState, LoginRequest, User } from '@types/user'
import { authApi } from '@services/auth'

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      // 登录
      login: async (credentials: LoginRequest) => {
        const response = await authApi.login(credentials)

        // 保存token和用户信息
        localStorage.setItem('access_token', response.access_token)
        set({
          user: response.user,
          token: response.access_token,
          isAuthenticated: true,
        })
      },

      // 登出
      logout: () => {
        localStorage.removeItem('access_token')
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
      },

      // 检查认证状态
      checkAuth: async () => {
        const token = localStorage.getItem('access_token')
        if (token) {
          try {
            const user = await authApi.getCurrentUser()
            set({
              user,
              token,
              isAuthenticated: true,
            })
          } catch (error) {
            // Token失效，清除状态
            get().logout()
          }
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: state => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
```

### 2.5 登录页面 (`src/pages/Login/index.tsx`)

```typescript
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, Typography, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useAuthStore } from '@store/authStore'
import { LoginRequest } from '@types/user'
import './Login.css'

const { Title, Text } = Typography

export const Login: React.FC = () => {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: LoginRequest) => {
    setLoading(true)
    try {
      await login(values)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (error) {
      // 错误已在interceptor中处理
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <Card className="login-card">
        <div className="login-header">
          <Title level={2}>影像数据平台</Title>
          <Text type="secondary">AI辅助报告筛选系统</Text>
        </div>

        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="邮箱"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="login-footer">
          <Text type="secondary">默认账号: admin@hospital.com / Admin@123456</Text>
        </div>
      </Card>
    </div>
  )
}
```

### 2.6 登录页面样式 (`src/pages/Login/Login.css`)

```css
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h2 {
  margin-bottom: 8px;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
}
```

### 2.7 受保护路由组件 (`src/components/Common/ProtectedRoute.tsx`)

```typescript
import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@store/authStore'
import { Spin } from 'antd'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, checkAuth } = useAuthStore()
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    const verify = async () => {
      await checkAuth()
      setLoading(false)
    }
    verify()
  }, [checkAuth])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}
```

**验收标准**:
- ✅ 登录页面UI完整美观
- ✅ 表单验证正常工作
- ✅ 登录成功后跳转到Dashboard
- ✅ Token正确存储在localStorage
- ✅ 受保护路由拦截未登录用户

---

## Phase 3: 布局框架开发 (Day 2下午 - 半天)

### 3.1 主布局组件 (`src/components/Layout/MainLayout.tsx`)

```typescript
import React, { useState } from 'react'
import { Layout, Menu, Avatar, Dropdown, Space, Typography } from 'antd'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import {
  DashboardOutlined,
  FileSearchOutlined,
  RobotOutlined,
  FolderOutlined,
  ImportOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@store/authStore'
import './MainLayout.css'

const { Header, Sider, Content } = Layout
const { Text } = Typography

export const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/import',
      icon: <ImportOutlined />,
      label: '数据导入',
    },
    {
      key: '/reports',
      icon: <FileSearchOutlined />,
      label: '报告检索',
    },
    {
      key: '/ai-analysis',
      icon: <RobotOutlined />,
      label: 'AI分析',
    },
    {
      key: '/projects',
      icon: <FolderOutlined />,
      label: '项目管理',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
    },
  ]

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        logout()
        navigate('/login')
      },
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div className="logo">
          <Text style={{ color: 'white', fontSize: collapsed ? '16px' : '18px' }}>
            {collapsed ? '影像' : '影像数据平台'}
          </Text>
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>

      <Layout>
        <Header className="site-layout-header">
          <Space style={{ marginLeft: 'auto' }}>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <Text>{user?.full_name || user?.email}</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ margin: '24px 16px', padding: 24, background: '#fff' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
```

### 3.2 布局样式 (`src/components/Layout/MainLayout.css`)

```css
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  transition: all 0.2s;
}

.site-layout-header {
  background: #fff;
  padding: 0 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
```

### 3.3 路由配置 (`src/App.tsx`)

```typescript
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { Login } from '@pages/Login'
import { MainLayout } from '@components/Layout/MainLayout'
import { ProtectedRoute } from '@components/Common/ProtectedRoute'
import { Dashboard } from '@pages/Dashboard'
import { DataImport } from '@pages/DataImport'
import { ReportSearch } from '@pages/ReportSearch'
import { AIAnalysis } from '@pages/AIAnalysis'
import { Projects } from '@pages/Projects'
import { Settings } from '@pages/Settings'

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <AntApp>
        <BrowserRouter>
          <Routes>
            {/* 公开路由 */}
            <Route path="/login" element={<Login />} />

            {/* 受保护路由 */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="import" element={<DataImport />} />
              <Route path="reports" element={<ReportSearch />} />
              <Route path="ai-analysis" element={<AIAnalysis />} />
              <Route path="projects" element={<Projects />} />
              <Route path="settings" element={<Settings />} />
            </Route>

            {/* 404 */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  )
}

export default App
```

**验收标准**:
- ✅ 侧边栏导航完整显示
- ✅ 侧边栏可折叠
- ✅ 菜单项高亮当前路由
- ✅ 用户头像和下拉菜单显示
- ✅ 退出登录功能正常
- ✅ 所有路由正确渲染

---

## Phase 4: 报告类型定义和API (Day 3上午 - 半天)

### 4.1 报告类型 (`src/types/report.ts`)

```typescript
// 报告接口
export interface Report {
  id: number
  patient_id: string
  patient_name: string
  patient_age: number | null
  patient_gender: string | null
  exam_date: string  // YYYY-MM-DD
  exam_type: string
  report_content: string
  diagnosis: string | null
  created_at: string
  updated_at: string
}

// 报告列表请求参数
export interface ReportListParams {
  page?: number
  page_size?: number
  q?: string  // 全文搜索关键词
  patient_id?: string
  exam_type?: string
  date_from?: string
  date_to?: string
  sort?: string
  order?: 'asc' | 'desc'
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
```

### 4.2 报告API (`src/services/reports.ts`)

```typescript
import apiClient from './api'
import { Report, ReportListParams, PaginatedResponse } from '@types/report'

export const reportsApi = {
  // 获取报告列表
  async getReports(params: ReportListParams): Promise<PaginatedResponse<Report>> {
    return apiClient.get<PaginatedResponse<Report>>('/reports', { params })
  },

  // 获取单个报告详情
  async getReportById(id: number): Promise<Report> {
    return apiClient.get<Report>(`/reports/${id}`)
  },

  // 删除报告
  async deleteReport(id: number): Promise<void> {
    return apiClient.delete(`/reports/${id}`)
  },

  // 批量删除报告
  async batchDeleteReports(ids: number[]): Promise<void> {
    return apiClient.post('/reports/batch-delete', { ids })
  },
}
```

### 4.3 报告状态管理 (`src/store/reportStore.ts`)

```typescript
import { create } from 'zustand'
import { Report, ReportListParams, PaginatedResponse } from '@types/report'
import { reportsApi } from '@services/reports'

interface ReportState {
  reports: Report[]
  total: number
  loading: boolean
  currentReport: Report | null

  // 操作
  fetchReports: (params: ReportListParams) => Promise<void>
  fetchReportById: (id: number) => Promise<void>
  deleteReport: (id: number) => Promise<void>
  clearCurrentReport: () => void
}

export const useReportStore = create<ReportState>((set, get) => ({
  reports: [],
  total: 0,
  loading: false,
  currentReport: null,

  // 获取报告列表
  fetchReports: async (params: ReportListParams) => {
    set({ loading: true })
    try {
      const response = await reportsApi.getReports(params)
      set({
        reports: response.items,
        total: response.total,
        loading: false,
      })
    } catch (error) {
      set({ loading: false })
      throw error
    }
  },

  // 获取报告详情
  fetchReportById: async (id: number) => {
    set({ loading: true })
    try {
      const report = await reportsApi.getReportById(id)
      set({ currentReport: report, loading: false })
    } catch (error) {
      set({ loading: false })
      throw error
    }
  },

  // 删除报告
  deleteReport: async (id: number) => {
    await reportsApi.deleteReport(id)
    // 从列表中移除
    set(state => ({
      reports: state.reports.filter(r => r.id !== id),
      total: state.total - 1,
    }))
  },

  // 清除当前报告
  clearCurrentReport: () => {
    set({ currentReport: null })
  },
}))
```

---

## Phase 5: 报告检索页面 (Day 3下午 + Day 4 - 1.5天)

### 5.1 搜索过滤器组件 (`src/components/Report/SearchFilters.tsx`)

```typescript
import React from 'react'
import { Form, Input, DatePicker, Select, Button, Space, Card } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { ReportListParams } from '@types/report'
import dayjs, { Dayjs } from 'dayjs'

const { RangePicker } = DatePicker

interface SearchFiltersProps {
  onSearch: (params: ReportListParams) => void
  loading?: boolean
}

export const SearchFilters: React.FC<SearchFiltersProps> = ({ onSearch, loading }) => {
  const [form] = Form.useForm()

  const handleSearch = () => {
    const values = form.getFieldsValue()
    const params: ReportListParams = {
      q: values.keyword,
      patient_id: values.patient_id,
      exam_type: values.exam_type,
    }

    // 处理日期范围
    if (values.date_range) {
      params.date_from = values.date_range[0].format('YYYY-MM-DD')
      params.date_to = values.date_range[1].format('YYYY-MM-DD')
    }

    onSearch(params)
  }

  const handleReset = () => {
    form.resetFields()
    onSearch({})
  }

  return (
    <Card>
      <Form form={form} layout="inline" onFinish={handleSearch}>
        <Form.Item name="keyword" style={{ width: 300 }}>
          <Input placeholder="搜索报告内容..." prefix={<SearchOutlined />} />
        </Form.Item>

        <Form.Item name="patient_id">
          <Input placeholder="患者ID" style={{ width: 150 }} />
        </Form.Item>

        <Form.Item name="exam_type">
          <Select placeholder="检查类型" style={{ width: 150 }} allowClear>
            <Select.Option value="CT">CT</Select.Option>
            <Select.Option value="MRI">MRI</Select.Option>
            <Select.Option value="X-Ray">X-Ray</Select.Option>
            <Select.Option value="Ultrasound">超声</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item name="date_range">
          <RangePicker format="YYYY-MM-DD" />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
              搜索
            </Button>
            <Button onClick={handleReset} icon={<ReloadOutlined />}>
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  )
}
```

### 5.2 报告表格组件 (`src/components/Report/ReportTable.tsx`)

```typescript
import React from 'react'
import { Table, Tag, Space, Button, Popconfirm, Tooltip } from 'antd'
import { EyeOutlined, DeleteOutlined, RobotOutlined } from '@ant-design/icons'
import { Report } from '@types/report'
import dayjs from 'dayjs'

interface ReportTableProps {
  reports: Report[]
  total: number
  loading: boolean
  page: number
  pageSize: number
  onPageChange: (page: number, pageSize: number) => void
  onView: (report: Report) => void
  onDelete: (id: number) => void
  onAnalyze: (report: Report) => void
}

export const ReportTable: React.FC<ReportTableProps> = ({
  reports,
  total,
  loading,
  page,
  pageSize,
  onPageChange,
  onView,
  onDelete,
  onAnalyze,
}) => {
  const columns = [
    {
      title: '患者ID',
      dataIndex: 'patient_id',
      key: 'patient_id',
      width: 120,
    },
    {
      title: '患者姓名',
      dataIndex: 'patient_name',
      key: 'patient_name',
      width: 100,
    },
    {
      title: '年龄/性别',
      key: 'patient_info',
      width: 100,
      render: (_: any, record: Report) => {
        const age = record.patient_age ?? '-'
        const gender = record.patient_gender ?? '-'
        return `${age} / ${gender}`
      },
    },
    {
      title: '检查日期',
      dataIndex: 'exam_date',
      key: 'exam_date',
      width: 120,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '检查类型',
      dataIndex: 'exam_type',
      key: 'exam_type',
      width: 100,
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '报告内容',
      dataIndex: 'report_content',
      key: 'report_content',
      ellipsis: {
        showTitle: false,
      },
      render: (content: string) => (
        <Tooltip title={content}>
          {content.length > 100 ? content.substring(0, 100) + '...' : content}
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: Report) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onView(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<RobotOutlined />}
            onClick={() => onAnalyze(record)}
          >
            AI分析
          </Button>
          <Popconfirm
            title="确认删除?"
            description="删除后无法恢复"
            onConfirm={() => onDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Table
      columns={columns}
      dataSource={reports}
      rowKey="id"
      loading={loading}
      pagination={{
        current: page,
        pageSize: pageSize,
        total: total,
        showSizeChanger: true,
        showTotal: total => `共 ${total} 条`,
        onChange: onPageChange,
      }}
      scroll={{ x: 1200 }}
    />
  )
}
```

### 5.3 报告详情抽屉 (`src/components/Report/ReportDetail.tsx`)

```typescript
import React from 'react'
import { Drawer, Descriptions, Tag, Divider, Typography } from 'antd'
import { Report } from '@types/report'
import dayjs from 'dayjs'

const { Paragraph } = Typography

interface ReportDetailProps {
  report: Report | null
  visible: boolean
  onClose: () => void
}

export const ReportDetail: React.FC<ReportDetailProps> = ({ report, visible, onClose }) => {
  if (!report) return null

  return (
    <Drawer
      title="报告详情"
      placement="right"
      width={720}
      open={visible}
      onClose={onClose}
    >
      <Descriptions bordered column={2}>
        <Descriptions.Item label="患者ID">{report.patient_id}</Descriptions.Item>
        <Descriptions.Item label="患者姓名">{report.patient_name}</Descriptions.Item>
        <Descriptions.Item label="年龄">{report.patient_age ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="性别">{report.patient_gender ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="检查日期">
          {dayjs(report.exam_date).format('YYYY-MM-DD')}
        </Descriptions.Item>
        <Descriptions.Item label="检查类型">
          <Tag color="blue">{report.exam_type}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="创建时间" span={2}>
          {dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}
        </Descriptions.Item>
      </Descriptions>

      <Divider>报告内容</Divider>
      <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{report.report_content}</Paragraph>

      {report.diagnosis && (
        <>
          <Divider>诊断结果</Divider>
          <Paragraph style={{ whiteSpace: 'pre-wrap' }}>{report.diagnosis}</Paragraph>
        </>
      )}
    </Drawer>
  )
}
```

### 5.4 报告检索页面 (`src/pages/ReportSearch/index.tsx`)

```typescript
import React, { useEffect, useState } from 'react'
import { Space, Button } from 'antd'
import { useNavigate } from 'react-router-dom'
import { RobotOutlined } from '@ant-design/icons'
import { SearchFilters } from '@components/Report/SearchFilters'
import { ReportTable } from '@components/Report/ReportTable'
import { ReportDetail } from '@components/Report/ReportDetail'
import { useReportStore } from '@store/reportStore'
import { Report, ReportListParams } from '@types/report'

export const ReportSearch: React.FC = () => {
  const navigate = useNavigate()
  const { reports, total, loading, fetchReports, deleteReport, currentReport, fetchReportById, clearCurrentReport } = useReportStore()

  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [searchParams, setSearchParams] = useState<ReportListParams>({})
  const [detailVisible, setDetailVisible] = useState(false)

  // 初始加载
  useEffect(() => {
    loadReports({})
  }, [])

  const loadReports = async (params: ReportListParams) => {
    const fullParams = {
      ...params,
      page,
      page_size: pageSize,
    }
    setSearchParams(params)
    await fetchReports(fullParams)
  }

  const handleSearch = (params: ReportListParams) => {
    setPage(1)
    loadReports(params)
  }

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setPage(newPage)
    setPageSize(newPageSize)
    loadReports({ ...searchParams, page: newPage, page_size: newPageSize })
  }

  const handleView = async (report: Report) => {
    await fetchReportById(report.id)
    setDetailVisible(true)
  }

  const handleCloseDetail = () => {
    setDetailVisible(false)
    clearCurrentReport()
  }

  const handleDelete = async (id: number) => {
    await deleteReport(id)
    // 重新加载当前页
    loadReports(searchParams)
  }

  const handleAnalyze = (report: Report) => {
    // 跳转到AI分析页面并传递报告ID
    navigate(`/ai-analysis?reportId=${report.id}`)
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <SearchFilters onSearch={handleSearch} loading={loading} />

      <ReportTable
        reports={reports}
        total={total}
        loading={loading}
        page={page}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        onView={handleView}
        onDelete={handleDelete}
        onAnalyze={handleAnalyze}
      />

      <ReportDetail
        report={currentReport}
        visible={detailVisible}
        onClose={handleCloseDetail}
      />
    </Space>
  )
}
```

**验收标准**:
- ✅ 搜索过滤器正常工作（关键词、患者ID、检查类型、日期范围）
- ✅ 报告列表表格展示完整
- ✅ 分页功能正常
- ✅ 查看详情抽屉显示完整报告信息
- ✅ 删除功能带确认提示
- ✅ "AI分析"按钮跳转到AI分析页面

---

## Phase 6-10: 其他功能模块

由于篇幅限制，剩余模块的详细实现请参考：

### Phase 6: 数据导入页面 (Day 5-6)
- Excel/CSV文件上传
- 字段映射配置
- 数据预览和验证
- 批量导入进度显示

### Phase 7: AI分析页面 (Day 7-9)
- 单报告AI分析表单
- 批量分析任务提交
- 提示词模板管理
- AI标注结果可视化（4种类型）

### Phase 8: 项目管理页面 (Day 10-11)
- 项目列表和卡片视图
- 创建/编辑项目
- 报告关联选择器
- 项目导出功能

### Phase 9: 仪表盘页面 (Day 12)
- 数据统计卡片
- 最近导入记录
- AI分析任务状态
- 快捷操作入口

### Phase 10: 设置页面 (Day 13)
- 个人资料编辑
- 密码修改表单

---

## 组件开发规范

### 文件组织规范

```
Component/
├── index.tsx           # 组件主文件
├── Component.css       # 组件样式（如果需要）
├── Component.test.tsx  # 组件测试（可选）
└── types.ts            # 组件特定类型（如果复杂）
```

### 组件命名规范

- **文件名**: PascalCase (如 `ReportTable.tsx`)
- **组件名**: 与文件名一致
- **CSS类名**: kebab-case (如 `report-table-container`)
- **类型名**: PascalCase + Interface/Type后缀

### React组件最佳实践

```typescript
import React, { useState, useEffect } from 'react'
import { Button } from 'antd'

// 1. Props接口定义
interface MyComponentProps {
  title: string
  count?: number  // 可选属性
  onSubmit: (value: string) => void
}

// 2. 函数组件声明
export const MyComponent: React.FC<MyComponentProps> = ({ title, count = 0, onSubmit }) => {
  // 3. useState hooks
  const [value, setValue] = useState('')

  // 4. useEffect hooks
  useEffect(() => {
    // 副作用逻辑
  }, [/* 依赖项 */])

  // 5. 事件处理函数
  const handleClick = () => {
    onSubmit(value)
  }

  // 6. 渲染逻辑
  return (
    <div>
      <h2>{title}</h2>
      <Button onClick={handleClick}>Submit</Button>
    </div>
  )
}
```

### TypeScript规范

```typescript
// ✅ 推荐：明确的类型定义
interface User {
  id: number
  name: string
  email: string
}

const user: User = { id: 1, name: 'Zhang San', email: 'zhang@example.com' }

// ❌ 避免：使用any
const data: any = fetchData()  // 不推荐

// ✅ 推荐：使用unknown并进行类型守卫
const data: unknown = fetchData()
if (isUser(data)) {
  console.log(data.email)
}
```

---

## 状态管理策略

### Zustand Store设计模式

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// 1. 定义状态接口
interface MyState {
  // 状态属性
  count: number
  user: User | null

  // 同步操作
  increment: () => void
  setUser: (user: User) => void

  // 异步操作
  fetchData: () => Promise<void>
}

// 2. 创建Store
export const useMyStore = create<MyState>()(
  persist(
    (set, get) => ({
      // 初始状态
      count: 0,
      user: null,

      // 同步操作
      increment: () => set(state => ({ count: state.count + 1 })),
      setUser: (user) => set({ user }),

      // 异步操作
      fetchData: async () => {
        const data = await api.fetchData()
        set({ user: data })
      },
    }),
    {
      name: 'my-storage',  // localStorage key
      partialize: (state) => ({ user: state.user }),  // 仅持久化user
    }
  )
)
```

### 在组件中使用Store

```typescript
import { useMyStore } from '@store/myStore'

export const MyComponent: React.FC = () => {
  // 选择性订阅（避免不必要的重渲染）
  const count = useMyStore(state => state.count)
  const increment = useMyStore(state => state.increment)

  // 或者使用浅比较订阅多个属性
  const { count, user, increment } = useMyStore(state => ({
    count: state.count,
    user: state.user,
    increment: state.increment,
  }), shallow)

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={increment}>Increment</button>
    </div>
  )
}
```

---

## API集成方案

### API服务层设计

```typescript
// src/services/example.ts
import apiClient from './api'
import { ExampleRequest, ExampleResponse } from '@types/example'

export const exampleApi = {
  // GET请求
  async getList(params: Record<string, any>): Promise<ExampleResponse[]> {
    return apiClient.get('/examples', { params })
  },

  // POST请求
  async create(data: ExampleRequest): Promise<ExampleResponse> {
    return apiClient.post('/examples', data)
  },

  // PUT请求
  async update(id: number, data: ExampleRequest): Promise<ExampleResponse> {
    return apiClient.put(`/examples/${id}`, data)
  },

  // DELETE请求
  async delete(id: number): Promise<void> {
    return apiClient.delete(`/examples/${id}`)
  },

  // 文件上传
  async upload(file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/examples/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
```

### 错误处理模式

```typescript
import { message } from 'antd'

// 在组件中
const handleSubmit = async () => {
  try {
    setLoading(true)
    await exampleApi.create(formData)
    message.success('创建成功')
    navigate('/list')
  } catch (error) {
    // 错误已在interceptor中统一处理
    // 这里只需要处理特定业务逻辑
  } finally {
    setLoading(false)
  }
}
```

---

## 路由设计

### 路由表配置

```typescript
// Phase 1路由规划
const routes = [
  { path: '/login', component: Login, public: true },
  { path: '/dashboard', component: Dashboard, protected: true },
  { path: '/import', component: DataImport, protected: true },
  { path: '/reports', component: ReportSearch, protected: true },
  { path: '/ai-analysis', component: AIAnalysis, protected: true },
  { path: '/projects', component: Projects, protected: true },
  { path: '/projects/:id', component: ProjectDetail, protected: true },
  { path: '/settings', component: Settings, protected: true },
]
```

### 编程式导航

```typescript
import { useNavigate } from 'react-router-dom'

const MyComponent: React.FC = () => {
  const navigate = useNavigate()

  const handleGoToDetail = (id: number) => {
    navigate(`/reports/${id}`)
  }

  const handleGoBack = () => {
    navigate(-1)
  }

  const handleGoToAnalysis = (reportId: number) => {
    navigate(`/ai-analysis?reportId=${reportId}`)
  }

  return <div>...</div>
}
```

---

## 测试策略

### 单元测试 (Vitest + React Testing Library)

#### 安装测试依赖

```bash
pnpm add -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

#### Vite测试配置 (`vite.config.ts`)

```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
```

#### 测试设置文件 (`src/test/setup.ts`)

```typescript
import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'

afterEach(() => {
  cleanup()
})
```

#### 组件测试示例

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ReportTable } from '@components/Report/ReportTable'

describe('ReportTable', () => {
  const mockReports = [
    { id: 1, patient_id: 'P001', patient_name: '张三', exam_date: '2024-01-01', exam_type: 'CT', report_content: '正常' },
  ]

  it('should render report table', () => {
    render(
      <ReportTable
        reports={mockReports}
        total={1}
        loading={false}
        page={1}
        pageSize={20}
        onPageChange={vi.fn()}
        onView={vi.fn()}
        onDelete={vi.fn()}
        onAnalyze={vi.fn()}
      />
    )

    expect(screen.getByText('P001')).toBeInTheDocument()
    expect(screen.getByText('张三')).toBeInTheDocument()
  })

  it('should call onView when view button is clicked', () => {
    const onView = vi.fn()
    render(
      <ReportTable
        reports={mockReports}
        onView={onView}
        {...otherProps}
      />
    )

    fireEvent.click(screen.getByText('查看'))
    expect(onView).toHaveBeenCalledWith(mockReports[0])
  })
})
```

### 运行测试

```bash
# 运行所有测试
pnpm test

# 监听模式
pnpm test --watch

# 生成覆盖率报告
pnpm test --coverage
```

---

## 性能优化

### 1. 代码分割和懒加载

```typescript
import React, { lazy, Suspense } from 'react'
import { Spin } from 'antd'

// 懒加载页面组件
const Dashboard = lazy(() => import('@pages/Dashboard'))
const ReportSearch = lazy(() => import('@pages/ReportSearch'))

const App: React.FC = () => {
  return (
    <Suspense fallback={<Spin size="large" />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/reports" element={<ReportSearch />} />
      </Routes>
    </Suspense>
  )
}
```

### 2. 使用React.memo避免不必要的重渲染

```typescript
import React, { memo } from 'react'

interface ReportCardProps {
  report: Report
  onClick: (id: number) => void
}

export const ReportCard = memo<ReportCardProps>(({ report, onClick }) => {
  return (
    <div onClick={() => onClick(report.id)}>
      <h3>{report.patient_name}</h3>
      <p>{report.report_content}</p>
    </div>
  )
}, (prevProps, nextProps) => {
  // 自定义比较逻辑
  return prevProps.report.id === nextProps.report.id
})
```

### 3. 使用useCallback和useMemo

```typescript
import React, { useCallback, useMemo } from 'react'

export const MyComponent: React.FC = () => {
  const [data, setData] = useState<Report[]>([])
  const [filter, setFilter] = useState('')

  // 缓存事件处理函数
  const handleClick = useCallback((id: number) => {
    console.log('Clicked:', id)
  }, [])

  // 缓存计算结果
  const filteredData = useMemo(() => {
    return data.filter(item => item.patient_name.includes(filter))
  }, [data, filter])

  return <div>...</div>
}
```

### 4. 虚拟滚动（大列表优化）

对于超长列表，使用`react-window`或`react-virtualized`：

```bash
pnpm add react-window
pnpm add -D @types/react-window
```

```typescript
import { FixedSizeList } from 'react-window'

const VirtualReportList: React.FC<{ reports: Report[] }> = ({ reports }) => {
  const Row = ({ index, style }: any) => (
    <div style={style}>
      {reports[index].patient_name}
    </div>
  )

  return (
    <FixedSizeList
      height={600}
      itemCount={reports.length}
      itemSize={50}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  )
}
```

### 5. 防抖和节流

```typescript
// 自定义防抖Hook
import { useState, useEffect } from 'react'

export const useDebounce = <T,>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

// 使用
const MyComponent: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const debouncedSearchTerm = useDebounce(searchTerm, 500)

  useEffect(() => {
    // 仅在用户停止输入500ms后才执行搜索
    if (debouncedSearchTerm) {
      performSearch(debouncedSearchTerm)
    }
  }, [debouncedSearchTerm])

  return <Input value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
}
```

---

## 部署流程

### 构建生产版本

```bash
# 1. 构建
pnpm build

# 2. 验证构建输出
ls -lh dist/

# 3. 本地预览生产构建
pnpm preview
```

### Dockerfile

```dockerfile
# 构建阶段
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package.json pnpm-lock.yaml ./

# 安装pnpm并安装依赖
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# 复制源代码
COPY . .

# 构建生产版本
RUN pnpm build

# 生产阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制Nginx配置（支持SPA路由）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx配置 (`nginx.conf`)

```nginx
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # SPA路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker Compose集成

在项目根目录的`docker-compose.yml`中添加前端服务：

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - backend
    environment:
      - VITE_API_BASE_URL=http://localhost:8000/api/v1
    networks:
      - app-network
```

---

## 开发检查清单

### 每日开发检查

- [ ] 代码遵循TypeScript严格模式
- [ ] 所有组件有明确的Props类型定义
- [ ] 使用ESLint检查并修复所有警告
- [ ] 新增组件添加基本的单元测试
- [ ] Git提交信息符合规范
- [ ] 本地开发服务器运行无错误

### 功能完成检查

- [ ] UI与设计稿一致
- [ ] 响应式布局在不同屏幕尺寸正常显示
- [ ] 表单验证完整
- [ ] 错误处理覆盖所有API调用
- [ ] Loading状态正确显示
- [ ] 空状态和错误状态有友好提示
- [ ] 可访问性（a11y）基本要求满足
- [ ] 浏览器控制台无错误和警告

### 性能检查

- [ ] 首屏加载时间 < 3秒
- [ ] 页面交互响应时间 < 100ms
- [ ] 长列表使用分页或虚拟滚动
- [ ] 图片和资源使用懒加载
- [ ] 无不必要的重渲染（使用React DevTools Profiler）

### 部署前检查

- [ ] 生产构建成功无错误
- [ ] 环境变量配置正确
- [ ] API端点指向生产环境
- [ ] 所有测试通过
- [ ] 代码已合并到main分支
- [ ] Docker镜像构建成功

---

## 常见问题和解决方案

### Q1: TypeScript路径别名不工作

**问题**: 使用`@/`导入时报错找不到模块

**解决方案**:
1. 检查`tsconfig.json`中的`paths`配置
2. 检查`vite.config.ts`中的`resolve.alias`配置
3. 重启VS Code和开发服务器

### Q2: Ant Design样式不生效

**问题**: 组件显示但没有样式

**解决方案**:
```typescript
// 在main.tsx中确保导入Ant Design样式
import 'antd/dist/reset.css'
```

### Q3: Zustand状态在页面刷新后丢失

**问题**: 页面刷新后状态重置

**解决方案**:
使用`persist`中间件持久化关键状态：

```typescript
import { persist } from 'zustand/middleware'

export const useMyStore = create<MyState>()(
  persist(
    (set, get) => ({ /* ... */ }),
    { name: 'my-storage' }
  )
)
```

### Q4: API请求CORS错误

**问题**: 开发时跨域请求被拦截

**解决方案**:
在`vite.config.ts`中配置代理：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

### Q5: 生产构建体积过大

**问题**: `dist/`目录超过500KB

**解决方案**:
1. 使用动态导入和代码分割
2. 分析bundle大小：`pnpm add -D rollup-plugin-visualizer`
3. 移除未使用的依赖
4. 开启Gzip压缩

---

## 总结

本前端开发工作流提供了完整的Phase 1前端实施指南，涵盖：

✅ **项目初始化**: Vite + React + TypeScript配置
✅ **架构设计**: 组件化、模块化目录结构
✅ **核心功能**: 认证、布局、报告检索完整实现
✅ **最佳实践**: TypeScript规范、状态管理、API集成
✅ **质量保证**: 测试策略、性能优化、部署流程

**预期开发周期**: 13天完成所有前端功能

**下一步**: 参考[后端开发工作流](./BACKEND_DEVELOPMENT_WORKFLOW.md)完成后端API实现，实现前后端联调。

---

**文档版本**: v1.0.0
**创建日期**: 2025-11-06
**维护团队**: 影像数据平台开发团队
