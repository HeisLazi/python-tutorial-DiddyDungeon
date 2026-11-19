import { Component } from 'react'

export default class OnlinePageBoundary extends Component {
  state = { failed: false, errorMessage: '' }

  static getDerivedStateFromError(error) {
    return { failed: true, errorMessage: error?.message || 'Unexpected page error.' }
  }

  componentDidCatch(error, info) {
    console.error('Online page failed to render.', error, info.componentStack)
  }

  componentDidUpdate(previousProps) {
    if (this.state.failed && previousProps.resetKey !== this.props.resetKey) {
      this.setState({ failed: false })
    }
  }

  render() {
    if (this.state.failed) {
      return <section className="online-page-error" role="alert" style={{ minHeight: 320, margin: '12px 0', background: '#24171c', color: '#eadcc9' }}>
        <h2>{this.props.pageName || 'Online page'} couldn’t open</h2>
        <p>The page hit an error while loading. Your online items and balance are unchanged.</p>
        {this.state.errorMessage && <code>{this.state.errorMessage}</code>}
        <button type="button" className="online-menu-secondary" onClick={this.props.onClose}>← Lobby</button>
      </section>
    }
    return this.props.children
  }
}
