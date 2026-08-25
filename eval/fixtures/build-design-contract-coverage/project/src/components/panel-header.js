// The shared screen header: title, subtitle, and the divider beneath them.
class PanelHeader {
  constructor({ title, subtitle }) {
    this.title = title;
    this.subtitle = subtitle;
  }

  render() {
    return {
      type: "header",
      className: "panel-header",
      children: [
        { type: "text", className: "panel-header__title", text: this.title },
        { type: "text", className: "panel-header__subtitle", text: this.subtitle },
      ],
    };
  }
}

module.exports = PanelHeader;
