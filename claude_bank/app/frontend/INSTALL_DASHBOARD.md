# BankX Operations Dashboard - Installation Guide

## 🎨 What's Been Built

A modern, beautiful dashboard for monitoring BankX multi-agent system with:
- ✅ **Tailwind CSS + Shadcn/ui** components (dark mode by default)
- ✅ **Dashboard Layout** with sidebar navigation
- ✅ **Agent Decisions Page** with 4 view modes (Table/Card/Timeline/Chart)
- ✅ **Comprehensive Filtering** (search, agent filter, status filter)
- ✅ **Mock Data** for development
- ✅ **Responsive Design** that works on all screen sizes

## 📦 Step 1: Install Dependencies

Navigate to the frontend directory:
```powershell
cd app\frontend
```

Install all dependencies:
```powershell
npm install
```

This will install:
- Tailwind CSS & PostCSS
- Shadcn/ui component primitives (@radix-ui/*)
- Lucide React icons
- Chart libraries (recharts)
- Utility libraries (clsx, tailwind-merge, date-fns)

## 🚀 Step 2: Start Development Server

```powershell
npm run dev
```

The application will be available at: **`http://localhost:8081`**

## 🎯 Step 3: Access the Dashboard

Open your browser and navigate to:
- **Main Chat**: `http://localhost:8081/#/`
- **Dashboard**: `http://localhost:8081/#/dashboard`

Or click "Dashboard" in the navigation menu.

## 🌙 Features

### Dark Mode
- Dark mode is enabled by default (modern look)
- Toggle with the sun/moon icon in the header
- Persists across page refreshes

### Agent Decisions Page
1. **Table View**: Sortable data table with all decision details
2. **Card View**: Grid of cards for easier reading
3. **Timeline View**: Chronological flow visualization
4. **Chart View**: Bar charts showing agent distribution

### Filters
- 🔍 **Search**: Search across queries and agent names
- 🤖 **Agent Filter**: Filter by specific agent (AccountAgent, ProdInfoFAQAgent, etc.)
- ✅ **Status Filter**: Filter by result status (success, failure, ticket_created)

## 📂 Files Created

```
app/frontend/
├── tailwind.config.js         # Tailwind configuration with dark mode
├── postcss.config.js           # PostCSS configuration
├── src/
│   ├── lib/
│   │   └── utils.ts            # Utility functions (cn helper)
│   ├── components/
│   │   └── ui/
│   │       ├── button.tsx      # Shadcn Button component
│   │       └── card.tsx        # Shadcn Card component
│   ├── data/
│   │   └── mockData.ts         # Mock observability data
│   └── pages/
│       └── dashboard/
│           ├── DashboardLayout.tsx        # Main layout with sidebar
│           ├── DashboardOverview.tsx      # Overview/home page
│           └── AgentDecisionsPage.tsx     # Agent decisions with 4 views
```

## 🔧 Configuration Updates

### tsconfig.json
Added path aliases for cleaner imports:
```json
{
  "baseUrl": ".",
  "paths": {
    "@/*": ["./src/*"]
  }
}
```

### vite.config.ts
Added path alias resolution:
```typescript
resolve: {
  alias: {
    "@": path.resolve(__dirname, "./src"),
  },
}
```

### index.css
Added Tailwind directives and dark mode CSS variables.

## 📊 Current Status

✅ **Phase 1 Complete**: Frontend with Mock Data
- Dashboard layout ✓
- Agent Decisions page (4 view modes) ✓
- Filtering system ✓
- Mock data ✓

⏳ **Phase 2 Next**: Additional Pages
- RAG Evaluations view
- Triage Rules view
- MCP Audit Trail view
- User Messages view
- Conversations browser

⏳ **Phase 3 Next**: Backend Integration
- Create API endpoints
- Connect frontend to real data
- Real-time updates

## 🎨 Design Highlights

- **Modern Color Scheme**: Blue/purple gradients with dark backgrounds
- **Smooth Animations**: Hover effects, transitions, loading states
- **Professional Typography**: Segoe UI system font stack
- **Accessible**: Proper contrast ratios, keyboard navigation
- **Performant**: Lazy loading, optimized re-renders

## 🐛 Troubleshooting

If you see TypeScript errors about missing modules:
```powershell
# Delete node_modules and reinstall
rm -r node_modules
npm install
```

If Tailwind classes aren't working:
```powershell
# Restart the dev server
# Press Ctrl+C, then run again:
npm run dev
```

## 📝 Next Steps

1. Test the dashboard by visiting `http://localhost:8081/#/dashboard`
2. Try all 4 view modes (Table/Card/Timeline/Chart)
3. Test the filtering (search, agent filter, status filter)
4. Toggle dark/light mode
5. Once satisfied with the UI, we'll build the remaining pages
6. Then connect to real backend API endpoints

## 🎉 You're Ready!

The dashboard is now set up with a beautiful, modern interface. Navigate to it and explore!
