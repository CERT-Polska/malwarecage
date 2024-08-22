import ELK, { ElkNode } from "elkjs/lib/elk.bundled.js";
import React, { useCallback, useLayoutEffect, useState } from "react";
import {
    ReactFlow,
    ReactFlowProvider,
    useReactFlow,
    Node as XYFlowNode,
    Edge as XYFlowEdge,
    Handle,
    Position,
    MarkerType,
    NodeChange,
    applyNodeChanges,
    applyEdgeChanges,
    EdgeChange,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";
import { Tag } from "@mwdb-web/types/types";

const elk = new ELK();

const elkOptions = {
    "elk.algorithm": "layered",
    "elk.layered.spacing.nodeNodeBetweenLayers": "100",
    "elk.spacing.nodeNode": "80",
    "elk.direction": "RIGHT",
};

type XYFlowGraph = {
    nodes: XYFlowNode[];
    edges: XYFlowEdge[];
};

type LayoutedNodeType = ElkNode & XYFlowNode;

async function layoutElements({
    nodes,
    edges,
}: XYFlowGraph): Promise<XYFlowGraph> {
    const graph: ElkNode = {
        id: "root",
        layoutOptions: elkOptions,
        children: nodes.map((node) => ({
            ...node,
            targetPosition: "left",
            sourcePosition: "top",
            width: 200,
            height: 210,
        })),
        edges: edges.map((edge) => ({
            ...edge,
            sources: [edge.source],
            targets: [edge.target],
        })),
    };

    const layoutedGraph = (await elk.layout(graph)) as LayoutedNodeType;
    const layoutedNodes = layoutedGraph.children as LayoutedNodeType[];
    return {
        nodes: layoutedNodes.map((node) => ({
            ...node,
            position: { x: node.x as number, y: node.y as number },
        })),
        edges: edges,
    };
}

type MWDBPlotNode = {
    id: string;
    expanded: boolean;
    object: {
        tags: Tag[];
        type: string;
        upload_time: string;
    };
};

type MWDBPlotEdge = {
    child: string;
    parent: string;
};

type MWDBGraph = {
    nodes: MWDBPlotNode[];
    edges: MWDBPlotEdge[];
};

type LayoutFlowNodeProps = {
    data: any;
    isConnectable: boolean;
};

function LayoutFlowNode({ data, isConnectable }: LayoutFlowNodeProps) {
    const NodeComponent = data.nodeComponent;
    return (
        <div
            style={{
                width: "fit-content",
                height: "fit-content",
                position: "relative",
            }}
        >
            <Handle
                type="target"
                position={Position.Left}
                isConnectable={isConnectable}
            />
            <NodeComponent node={{ ...data }} />
            <Handle
                type="source"
                position={Position.Right}
                isConnectable={isConnectable}
            />
        </div>
    );
}

type LayoutFlowProps = {
    nodeComponent: any;
    onNodeClick: (id: string) => void;
    width: number | string;
    height: number | string;
} & MWDBGraph;

function LayoutFlow({
    nodes,
    edges,
    nodeComponent,
    onNodeClick,
    width,
    height,
}: LayoutFlowProps) {
    const [xyGraph, setXYGraph] = useState<XYFlowGraph>({
        nodes: [],
        edges: [],
    });
    const onXYNodesChange = useCallback(
        (changes: NodeChange[]) => {
            setXYGraph((graph) => {
                // BUG: Sometimes NaN value appears in position, we need to ignore these updates
                if (
                    changes.some(
                        (change) =>
                            change.type == "position" &&
                            (!change.position || isNaN(change.position.x))
                    )
                )
                    return graph;
                return {
                    nodes: applyNodeChanges(changes, graph.nodes),
                    edges: graph.edges,
                };
            });
        },
        [setXYGraph]
    );
    const onXYEdgesChange = useCallback(
        (changes: EdgeChange[]) => {
            setXYGraph((graph) => {
                return {
                    nodes: graph.nodes,
                    edges: applyEdgeChanges(changes, graph.edges),
                };
            });
        },
        [setXYGraph]
    );
    const { fitView } = useReactFlow();

    const doLayout = useCallback(
        async (mwdbGraph: MWDBGraph) => {
            const getPosition = (node: MWDBPlotNode) => {
                // Preserve position of nodes on update
                const xynode = xyGraph.nodes.find(
                    (xynode) => xynode.id == node.id
                );
                return xynode ? xynode.position : { x: 0, y: 0 };
            };
            const graph = {
                nodes: nodes.map((node) => ({
                    id: node.id,
                    type: "node",
                    data: {
                        ...node,
                        onClick: () => onNodeClick(node.id),
                        nodeComponent: nodeComponent,
                    },
                    position: getPosition(node),
                })),
                edges: edges.map((edge) => ({
                    id: `e${edge.parent}_${edge.child}`,
                    source: edge.parent,
                    target: edge.child,
                    type: "smoothstep",
                    markerEnd: {
                        type: MarkerType.Arrow,
                    },
                })),
            };
            const layoutedGraph = await layoutElements(graph);
            setXYGraph({
                nodes: layoutedGraph.nodes,
                edges: layoutedGraph.edges,
            });
        },
        [setXYGraph, xyGraph, onNodeClick, nodeComponent]
    );

    // Calculate the initial layout on mount.
    useLayoutEffect(() => {
        doLayout({ nodes, edges }).then(() => fitView());
    }, [nodes, edges, onNodeClick, nodeComponent]);

    return (
        <div style={{ width, height }}>
            <ReactFlow
                nodes={xyGraph.nodes}
                edges={xyGraph.edges}
                onNodesChange={onXYNodesChange}
                onEdgesChange={onXYEdgesChange}
                fitView
                nodesConnectable={false}
                nodeTypes={{
                    node: LayoutFlowNode,
                }}
            />
        </div>
    );
}

export default (props: LayoutFlowProps) => (
    <ReactFlowProvider>
        <LayoutFlow {...props} />
    </ReactFlowProvider>
);
