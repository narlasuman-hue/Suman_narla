# Database Metadata Catalog - React Frontend

A modern React 18 dashboard for browsing and managing database metadata, with features for lineage analysis, asset lifecycle management, and data discovery.

## Features

- **Dashboard** - Overview of catalog statistics and quick access to key features
- **Search** - Full-text search across tables, columns, databases with autocomplete
- **Lineage Visualization** - View upstream sources and downstream targets for tables
- **Asset Details** - Comprehensive information about tables, columns, and databases
- **Lifecycle Management** - Track asset status (active, deprecated, decommissioned)
- **Reports & Analytics** - View storage usage, most-used tables, data quality scores
- **Query Analysis** - Identify heavy users and query patterns
- **Impact Analysis** - Understand dependencies before making changes

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type-safe JavaScript
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first CSS
- **Axios** - HTTP client
- **Zustand** - State management (if needed)
- **Recharts** - Data visualization
- **React Icons** - Icon library
- **React Hot Toast** - Notifications

## Installation

### Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Setup

1. **Install dependencies**

```bash
npm install
```

2. **Configure environment**

```bash
cp .env.example .env
```

Edit `.env` if your backend API is on a different URL:

```env
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_ENV=development
```

3. **Start development server**

```bash
npm start
```

The app will open at `http://localhost:3000`

## Development

### Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/       # Reusable React components
│   │   ├── Layout.tsx    # Main layout with sidebar
│   │   ├── Header.tsx    # Top navigation
│   │   ├── Sidebar.tsx   # Navigation menu
│   │   ├── StatCard.tsx  # Statistics display
│   │   └── LoadingSpinner.tsx
│   ├── pages/           # Page components
│   │   ├── Dashboard.tsx
│   │   ├── SearchPage.tsx
│   │   ├── AssetDetail.tsx
│   │   ├── LineagePage.tsx
│   │   ├── ReportsPage.tsx
│   │   ├── LifecyclePage.tsx
│   │   └── QueryAnalysisPage.tsx
│   ├── services/        # API client
│   │   └── api.ts       # Axios configuration and API methods
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   ├── styles/          # Global styles
│   │   └── globals.css  # Tailwind CSS imports
│   ├── App.tsx          # Main app component with routing
│   └── index.tsx        # React DOM render
├── tailwind.config.js   # Tailwind configuration
├── postcss.config.js    # PostCSS configuration
├── tsconfig.json        # TypeScript configuration
├── package.json         # Dependencies
└── .env                 # Environment variables
```

### Key Components

#### Layout

The `Layout` component provides the main structure with a collapsible sidebar and header.

```tsx
<Layout>
  <Routes>
    <Route path="/" element={<Dashboard />} />
    {/* More routes */}
  </Routes>
</Layout>
```

#### Pages

Each page component handles its own data fetching and state management:

- **Dashboard** - Summary statistics and recent assets
- **SearchPage** - Global search with filters and autocomplete
- **AssetDetail** - Detailed view of tables/databases with columns
- **LineagePage** - Upstream/downstream lineage visualization
- **ReportsPage** - Charts and analytics
- **LifecyclePage** - Asset lifecycle tracking
- **QueryAnalysisPage** - Query patterns and heavy users

#### API Service

The `api.ts` service provides typed API methods:

```typescript
// Fetch databases
const databases = await getDatabases();

// Search for tables
const results = await searchTables('customer');

// Get lineage
const lineage = await getFullLineage(tableId);

// Deprecate asset
await deprecateAsset(tableId, 'No longer in use');
```

## Available Scripts

### Development

```bash
npm start
```

Runs the app in development mode with hot reload.

### Production Build

```bash
npm run build
```

Builds the app for production to `build/` directory.

### Testing

```bash
npm test
```

Runs tests in interactive watch mode.

### Linting & Formatting

```bash
npm run lint
npm run format
```

## API Integration

The frontend communicates with the backend API at `/api/v1`:

- **Health checks** - `GET /health`, `GET /health/db`
- **Databases** - `GET /databases`, `GET /databases/{id}`
- **Tables** - `GET /tables`, `GET /tables/{id}`, `GET /tables/{id}/columns`
- **Lineage** - `GET /lineage/{id}/upstream`, `/downstream`, `/full`
- **Search** - `GET /search`, `GET /search/tables`, `GET /search/columns`
- **Lifecycle** - `GET /lifecycle/summary`, `POST /lifecycle/assets/{id}/deprecate`
- **Reports** - `GET /reports/summary`, `GET /reports/storage-usage`
- **Analysis** - `GET /analysis/heavy-users`, `POST /analysis/parse-logs`

See backend [API documentation](../docs/API.md) for details.

## Styling

The project uses **Tailwind CSS** for styling. Customize colors and themes in `tailwind.config.js`.

### Color Scheme

- **Primary**: Blue (`#3b82f6`)
- **Success**: Green (`#10b981`)
- **Warning**: Orange (`#f59e0b`)
- **Error**: Red (`#ef4444`)
- **Info**: Purple (`#a855f7`)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REACT_APP_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API URL |
| `REACT_APP_ENV` | `development` | Environment (development/production) |

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Troubleshooting

### API Connection Issues

1. **Ensure backend is running** on the configured URL
2. **Check CORS settings** - Backend should allow frontend origin
3. **Verify API_BASE_URL** in `.env` matches backend address

### Build Issues

1. **Clear node_modules** - `rm -rf node_modules && npm install`
2. **Clear cache** - `npm cache clean --force`
3. **Delete build** - `rm -rf build/`

### UI Not Displaying Correctly

1. **Clear browser cache** - Hard refresh (Ctrl+Shift+R)
2. **Rebuild Tailwind** - Restart dev server
3. **Check console** - Look for TypeScript or runtime errors

## Performance Optimization

- Lazy load pages with React Router
- Memoize components to prevent unnecessary re-renders
- Paginate large datasets (tables, search results)
- Cache API responses with appropriate TTL
- Use request debouncing for search and autocomplete

## Future Enhancements

- [ ] Authentication and authorization
- [ ] Dark mode toggle
- [ ] Customizable dashboard widgets
- [ ] Interactive lineage graph with Cytoscape.js
- [ ] Advanced search filters
- [ ] Saved searches and favorites
- [ ] Export functionality (CSV, PDF)
- [ ] Data quality scorecards
- [ ] Change audit trail
- [ ] Notifications and alerts

## Contributing

1. Follow the existing code style and patterns
2. Use TypeScript for type safety
3. Write meaningful commit messages
4. Test changes before submitting
5. Update documentation as needed

## License

Mozilla Public License 2.0 - See [LICENSE](../LICENSE)

## Support

For issues or questions:
1. Check the [backend API documentation](../docs/API.md)
2. Review [lineage documentation](../docs/LINEAGE.md)
3. Check [search documentation](../docs/SEARCH.md)
4. Refer to [development guide](../docs/DEVELOPMENT.md)
