# Feature Request: Snap to Grid for Node Editor

## Motivation

Users benefit from a "snap to grid" feature in node editors because it helps keep node layouts tidy, visually aligned, and easier to read. This is especially useful in large graphs or when sharing screenshots/documentation.

## Technical Explanation

Qt's `QGraphicsItem` provides a method called `itemChange`, which is called whenever certain properties of the item change. For node movement, two relevant change types are:

- `QGraphicsItem.ItemPositionChange`: Called **before** the item's position is changed. You can return a modified position here to implement snapping.
- `QGraphicsItem.ItemPositionHasChanged`: Called **after** the item's position has changed. (Currently used to emit signals.)

To implement snap to grid, logic should be added to `NodeItem.itemChange` for the `ItemPositionChange` case. The new position should be rounded to the nearest grid point (e.g., 20px increments).

## Configurability

The grid size (snap interval) should be configurable, ideally as a constant in `theme.py` (e.g., `NODE_GRID_SIZE = 20.0`).

## Code Areas to Update

- `src/edon_ui/item/node.py`:
  - `NodeItem.itemChange`: Add logic for `ItemPositionChange` to snap the new position to the grid.
- `src/edon_ui/theme.py`:
  - Add a constant for grid size.
- (Optional) `GraphController` or other code that moves nodes programmatically should also use the grid.

## Example Implementation

```python
# In NodeItem.itemChange:
if change == QGraphicsItem.ItemPositionChange:
    new_pos = value
    grid_size = theme.NODE_GRID_SIZE
    snapped_x = round(new_pos.x() / grid_size) * grid_size
    snapped_y = round(new_pos.y() / grid_size) * grid_size
    return QPointF(snapped_x, snapped_y)
```

## References
- See this conversation for rationale and user experience context.
- Qt documentation: https://doc.qt.io/qt-6/qgraphicsitem.html#itemChange

---

**Feature Request** 