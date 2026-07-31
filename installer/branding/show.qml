/* SPDX-License-Identifier: GPL-3.0-or-later */

import QtQuick 2.0
import calamares.slideshow 1.0

Presentation {
    Slide {
        Image {
            id: background
            source: "welcome.svg"
            width: parent.width
            height: parent.height * 0.78
            fillMode: Image.PreserveAspectCrop
            anchors.top: parent.top
        }
        Text {
            anchors.horizontalCenter: background.horizontalCenter
            anchors.top: background.bottom
            width: parent.width * 0.9
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "#172133"
            text: qsTr("正在安装落川OS 300型，请保持电脑接通电源。")
        }
    }
}
