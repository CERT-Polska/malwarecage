import React, {
    Suspense,
    useState,
    useLayoutEffect,
    useContext,
    useEffect,
} from "react";
import { isEmpty } from "lodash";
import { useSearchParams } from "react-router-dom";

import { APIContext } from "@mwdb-web/commons/api";
import { RelationsNode } from "../RelationsNode";
import { RelationToManyNode } from "../RelationToManyNode";
import { Edge, NodeProp, RelatedObject } from "@mwdb-web/types/types";
import XYFlowPlot from "../XYFlowPlot";

const nodeStatuses = {
    initial: "initial",
    showGraph: "showGraph",
    showWarning: "showWarning",
};

type RelationUpdateType = "children" | "parent" | null;

type Nodes = {
    nodes: NodeProp[];
    edges: Edge[];
};

type Props = {
    hash?: string;
    height?: string;
};

export function RelationsPlotView(props: Props) {
    const api = useContext(APIContext);
    const [searchParams, setSearchParams] = useSearchParams();
    const { hash, height } = props;
    const defaultProps = {
        height: 900,
        width: "100%",
    };

    const [nodesStatus, setNodesStatus] = useState("initial");

    const [nodes, setNodes] = useState<Nodes>({
        nodes: [],
        edges: [],
    });

    const convertObject = (obj: RelatedObject, expanded: boolean) => {
        const node: NodeProp = {
            id: obj.id,
            object: {
                type: obj.type,
                upload_time: obj.upload_time,
                tags: obj.tags,
            },
            expanded,
        };
        return node;
    };

    const isNodeExpanded = (hash: string) => {
        let node = nodes.nodes.find((n) => n.id === hash);
        return node && node.expanded;
    };

    const addNodes = (
        prevNodesState: Nodes,
        newNode: RelatedObject,
        newEdge?: Edge
    ) => {
        const getNode = (hash: string) => {
            return prevNodesState.nodes.find((n) => n.id === hash);
        };

        const getEdge = (edge: Edge) => {
            return prevNodesState.edges.find(
                (e) => e.parent === edge.parent && e.child === edge.child
            );
        };

        const newNodesState = {} as Nodes;
        let existingNode = getNode(newNode.id);
        if (!existingNode) {
            // Append new node and mark node as expanded if no edge is added.
            newNodesState.nodes = [
                ...prevNodesState.nodes,
                convertObject(newNode, !newEdge),
            ];
        } else {
            // Update node in the same place
            let newConvertNode = {} as NodeProp;
            if ((!existingNode.expanded && !newEdge) || existingNode.expanded)
                newConvertNode = convertObject(newNode, true);
            else newConvertNode = convertObject(newNode, false);
            newNodesState.nodes = prevNodesState.nodes.reduce(
                (nodesList: NodeProp[], node: NodeProp) => {
                    if (node.id === newNode.id)
                        return [...nodesList, newConvertNode];
                    else return [...nodesList, node];
                },
                []
            );
        }
        if (newEdge && !getEdge(newEdge)) {
            newNodesState.edges = [...prevNodesState.edges, newEdge];
        } else {
            newNodesState.edges = [...prevNodesState.edges];
        }
        return newNodesState;
    };

    const updateObject = (
        obj: RelatedObject,
        type: RelationUpdateType = null,
        edgeId: string | null = null
    ) => {
        if (type === "parent") {
            setNodes((prevNodes) =>
                addNodes(prevNodes, obj, {
                    parent: obj.id,
                    child: edgeId as string,
                })
            );
        } else if (type === "children") {
            setNodes((prevNodes) =>
                addNodes(prevNodes, obj, {
                    parent: edgeId as string,
                    child: obj.id,
                })
            );
        } else {
            setNodes((prevNodes) => addNodes(prevNodes, obj));
        }
    };

    const expandNode = async (hash: string) => {
        const objectInfo = await api.getObject("object", hash);
        const obj = objectInfo.data;
        updateObject(obj);
        if (obj.parents.length > 0) {
            obj.parents.forEach((o) => {
                updateObject(o, "parent", obj.id);
            });
        }
        if (obj.children.length > 0) {
            obj.children.forEach((o) => {
                updateObject(o, "children", obj.id);
            });
        }
    };

    const onNodeClick = (node: string) => {
        let nodes = searchParams.getAll("node");
        if (isNodeExpanded(node)) return;
        nodes = [...(nodes || []), node];
        expandNode(node);
        setSearchParams(
            new URLSearchParams(nodes.map((node) => ["node", node])),
            { replace: true }
        );
    };

    useLayoutEffect(() => {
        const nodes = searchParams.getAll("node");
        const expandedNodes = nodes || [];
        if (hash && !expandedNodes.includes(hash)) {
            expandedNodes.push(hash);
        }
        for (let node of expandedNodes) expandNode(node);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        const limit = 500;
        if (!isEmpty(nodes.nodes) || !isEmpty(nodes.edges)) {
            const elementsLength = Math.max(
                nodes.nodes.length,
                nodes.edges.length
            );
            setNodesStatus(
                elementsLength < limit
                    ? nodeStatuses.showGraph
                    : nodeStatuses.showWarning
            );
        }
    }, [nodes]);

    return (
        <Suspense fallback={<div />}>
            {nodesStatus === nodeStatuses.showGraph && (
                <XYFlowPlot
                    width={defaultProps.width}
                    height={height ? +height : defaultProps.height}
                    nodes={nodes.nodes}
                    edges={nodes.edges}
                    onNodeClick={onNodeClick}
                    nodeComponent={RelationsNode}
                />
            )}
            {nodesStatus === nodeStatuses.showWarning && (
                <RelationToManyNode
                    setNodesStatus={setNodesStatus}
                    nodesLength={Math.max(
                        nodes.nodes.length,
                        nodes.edges.length
                    )}
                />
            )}
        </Suspense>
    );
}
