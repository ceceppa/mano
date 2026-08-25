// The shared single-indicator selector. Buttons carry label and focus only;
// the dock owns the one moving indicator that marks the selection.
class SegmentedControl {
  constructor({ options, selected, onSelect }) {
    this.options = options;
    this.selected = selected;
    this.onSelect = onSelect;
  }

  select(option) {
    this.selected = option;
    if (this.onSelect) this.onSelect(option);
  }

  render() {
    return {
      type: "dock",
      className: "segmented-control",
      indicatorAt: this.options.indexOf(this.selected),
      children: this.options.map((option) => ({
        type: "button",
        className: "segmented-control__item",
        text: option,
        onPress: () => this.select(option),
      })),
    };
  }
}

module.exports = SegmentedControl;
