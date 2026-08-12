import type { Bean } from '../context/bean';
import type { GridOptions } from '../entities/gridOptions';
import type { ITreeNode, RowNode } from '../entities/rowNode';
import type { ChangedPath } from '../utils/changedPath';
import type { ClientSideRowModelStage, IChangedRowNodes } from './iClientSideRowModel';
export interface RowGroupingRowNode<TData = any> extends RowNode<TData> {
    parent: RowGroupingRowNode<TData> | null;
    allLeafChildren: RowGroupingRowNode<TData>[] | null;
    childrenAfterGroup: RowGroupingRowNode<TData>[] | null;
    treeNode: ITreeNode | null;
    treeNodeFlags: number;
    sibling: RowGroupingRowNode<TData>;
    sourceRowIndex: number;
}
export interface StageExecuteParams<TData = any> {
    rowNode: RowNode<TData>;
    changedRowNodes?: IChangedRowNodes<TData>;
    rowNodesOrderChanged?: boolean;
    changedPath?: ChangedPath;
    afterColumnsChanged?: boolean;
}
export interface IRowGroupingStrategy<TData = any> extends Bean {
    execute(params: StageExecuteParams<TData>): void;
}
export interface IRowNodeStage<TResult = any, TData = any> {
    step: ClientSideRowModelStage;
    refreshProps: Set<keyof GridOptions>;
    execute(params: StageExecuteParams<TData>): TResult;
}
