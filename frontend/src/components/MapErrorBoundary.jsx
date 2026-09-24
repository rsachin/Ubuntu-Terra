import { Component } from 'react';

export default class MapErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error('Map failed to render:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="field-map field-map--fallback">
          Map couldn't load in this environment. Use the list below to select a field.
        </div>
      );
    }
    return this.props.children;
  }
}
