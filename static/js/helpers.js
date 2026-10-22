export function horizontalMerge(list1, list2) {
    let returnList = [];

    for (let i = 0; i < longestList(list1, list2).length; i++) {
        const item1 = list1[i];
        const item2 = list2[i];

        returnList.push({item1, item2});
    }

    return returnList;
}

function longestList(list1, list2) {
    return list1.length >= list2.length ? list1 : list2;
}