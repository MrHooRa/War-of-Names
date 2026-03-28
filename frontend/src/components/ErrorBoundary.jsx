import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('App Error:', error, errorInfo)
    // Future: send to Sentry
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-brand-light-bg dark:bg-brand-dark-bg flex items-center justify-center p-6" dir="rtl">
          <div className="text-center space-y-4">
            <iconify-icon icon="lucide:alert-triangle" class="text-6xl text-brand-danger"></iconify-icon>
            <h1 className="font-display text-2xl font-black text-gray-900 dark:text-white">حدث خطأ غير متوقع</h1>
            <p className="text-gray-500 dark:text-gray-400 font-bold">نعتذر عن هذا الخطأ. يرجى تحديث الصفحة.</p>
            <button
              onClick={() => window.location.reload()}
              className="bg-brand-teal text-white px-6 py-3 rounded-xl font-bold hover:bg-brand-teal-hover smooth-transition"
            >
              تحديث الصفحة
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
