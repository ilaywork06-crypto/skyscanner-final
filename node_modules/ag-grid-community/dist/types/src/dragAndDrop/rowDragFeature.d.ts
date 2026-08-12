import { BeanStub } from '../context/beanStub';
import type { RowDragCancelEvent, RowDragEndEvent, RowDragEnterEvent, RowDragLeaveEvent, RowDragMoveEvent } from '../events';
import type { DragAndDropIcon, DraggingEvent, DropTarget } from './dragAndDropService';
import { DragSourceType } from './dragAndDropService';
export interface RowDropZoneEvents {
    /** Callback function that will be executed when the rowDrag enters the target. */
    onDragEnter?: (params: RowDragEnterEvent) => void;
    /** Callback function that will be executed when the rowDrag leaves the target */
    onDragLeave?: (params: RowDragLeaveEvent) => void;
    /**
     * Callback function that will be executed when the rowDrag is dragged inside the target.
     * Note: this gets called multiple times.
     */
    onDragging?: (params: RowDragMoveEvent) => void;
    /** Callback function that will be executed when the rowDrag drops rows within the target. */
    onDragStop?: (params: RowDragEndEvent) => void;
    onDragCancel?: (params: RowDragCancelEvent) => void;
}
export interface RowDropZoneParams extends RowDropZoneEvents {
    /** A callback method that returns the DropZone HTMLElement. */
    getContainer: () => HTMLElement;
}
export declare class RowDragFeature extends BeanStub implements DropTarget {
    private clientSideRowModel;
    private eContainer;
    private lastDraggingEvent;
    private autoScrollService;
    constructor(eContainer: HTMLElement);
    postConstruct(): void;
    getContainer(): HTMLElement;
    isInterestedIn(type: DragSourceType): boolean;
    getIconName(): DragAndDropIcon;
    shouldPreventRowMove(): boolean;
    private getRowNodes;
    onDragEnter(draggingEvent: DraggingEvent): void;
    onDragging(draggingEvent: DraggingEvent): void;
    private isFromThisGrid;
    private onEnterOrDragging;
    private doManagedDrag;
    private getRowIndexNumber;
    private getRowsDrop;
    /** When dragging multiple rows, we want the user to be able to drag to the prev or next in the group if dragging on one of the selected rows. */
    private getPrevOrNext;
    addRowDropZone(params: RowDropZoneParams & {
        fromGrid?: boolean;
    }): void;
    getRowDropZone(events?: RowDropZoneEvents): RowDropZoneParams;
    private draggingToRowDragEvent;
    private dispatchGridEvent;
    onDragLeave(draggingEvent: DraggingEvent): void;
    onDragStop(draggingEvent: DraggingEvent): void;
    onDragCancel(draggingEvent: DraggingEvent): void;
    private stopDragging;
    private setRowNodeDragging;
    /** Drag and drop. Returns false if at least a row was moved, otherwise true */
    private dropRows;
    private addRows;
    private moveRows;
    /** Creates a set of valid rows to move, filtering out rows that are not leafs or are not in the current model (deleted) */
    private getValidRowsToMove;
    /** For reorderLeafChildren, returns min index of the rows to move, the target index and the max index of the rows to move. */
    private getMoveRowsBounds;
    /** Reorders the children of the root node, so that the rows to move are in the correct order.
     * @param rowsToMoveSet The valid set of rows to move, as returned by getValidRowsToMove
     * @param firstAffectedLeafIdx The first index of the rows to move
     * @param targetPositionIdx The target index, where the rows will be moved
     * @param lastAffectedLeafIndex The last index of the rows to move
     * @returns True if the order of the rows changed, false otherwise
     */
    private reorderLeafChildren;
}
