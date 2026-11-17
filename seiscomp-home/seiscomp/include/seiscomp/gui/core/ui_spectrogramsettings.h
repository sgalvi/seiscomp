/********************************************************************************
** Form generated from reading UI file 'spectrogramsettings.ui'
**
** Created by: Qt User Interface Compiler version 5.15.13
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_SPECTROGRAMSETTINGS_H
#define UI_SPECTROGRAMSETTINGS_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QDoubleSpinBox>
#include <QtWidgets/QFrame>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_SpectrogramSettings
{
public:
    QVBoxLayout *verticalLayout;
    QFrame *frame;
    QGridLayout *gridLayout;
    QLabel *label_9;
    QLabel *label;
    QCheckBox *cbSmoothing;
    QLabel *label_2;
    QCheckBox *cbLogScale;
    QLabel *label_3;
    QLabel *label_4;
    QDoubleSpinBox *spinMinAmp;
    QLabel *label_5;
    QDoubleSpinBox *spinMaxAmp;
    QLabel *label_6;
    QDoubleSpinBox *spinTimeWindow;
    QLabel *label_7;
    QDoubleSpinBox *spinOverlap;
    QLabel *label_8;
    QCheckBox *cbShowAxis;
    QLabel *label_10;
    QDoubleSpinBox *spinMinFrequency;
    QDoubleSpinBox *spinMaxFrequency;
    QComboBox *cbNormalization;
    QHBoxLayout *horizontalLayout;
    QSpacerItem *horizontalSpacer;
    QPushButton *btnApply;
    QSpacerItem *verticalSpacer;

    void setupUi(QWidget *SpectrogramSettings)
    {
        if (SpectrogramSettings->objectName().isEmpty())
            SpectrogramSettings->setObjectName(QString::fromUtf8("SpectrogramSettings"));
        SpectrogramSettings->resize(541, 503);
        verticalLayout = new QVBoxLayout(SpectrogramSettings);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        frame = new QFrame(SpectrogramSettings);
        frame->setObjectName(QString::fromUtf8("frame"));
        frame->setFrameShape(QFrame::StyledPanel);
        frame->setFrameShadow(QFrame::Raised);
        gridLayout = new QGridLayout(frame);
        gridLayout->setObjectName(QString::fromUtf8("gridLayout"));
        label_9 = new QLabel(frame);
        label_9->setObjectName(QString::fromUtf8("label_9"));
        label_9->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_9, 6, 0, 1, 1);

        label = new QLabel(frame);
        label->setObjectName(QString::fromUtf8("label"));
        QSizePolicy sizePolicy(QSizePolicy::Preferred, QSizePolicy::Preferred);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(label->sizePolicy().hasHeightForWidth());
        label->setSizePolicy(sizePolicy);
        label->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label, 0, 0, 1, 1);

        cbSmoothing = new QCheckBox(frame);
        cbSmoothing->setObjectName(QString::fromUtf8("cbSmoothing"));
        QSizePolicy sizePolicy1(QSizePolicy::MinimumExpanding, QSizePolicy::Fixed);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(cbSmoothing->sizePolicy().hasHeightForWidth());
        cbSmoothing->setSizePolicy(sizePolicy1);

        gridLayout->addWidget(cbSmoothing, 0, 1, 1, 1);

        label_2 = new QLabel(frame);
        label_2->setObjectName(QString::fromUtf8("label_2"));
        label_2->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_2, 1, 0, 1, 1);

        cbLogScale = new QCheckBox(frame);
        cbLogScale->setObjectName(QString::fromUtf8("cbLogScale"));

        gridLayout->addWidget(cbLogScale, 1, 1, 1, 1);

        label_3 = new QLabel(frame);
        label_3->setObjectName(QString::fromUtf8("label_3"));
        label_3->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_3, 2, 0, 1, 1);

        label_4 = new QLabel(frame);
        label_4->setObjectName(QString::fromUtf8("label_4"));
        label_4->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_4, 4, 0, 1, 1);

        spinMinAmp = new QDoubleSpinBox(frame);
        spinMinAmp->setObjectName(QString::fromUtf8("spinMinAmp"));
        spinMinAmp->setMinimum(-99.989999999999995);
        spinMinAmp->setValue(-15.000000000000000);

        gridLayout->addWidget(spinMinAmp, 4, 1, 1, 1);

        label_5 = new QLabel(frame);
        label_5->setObjectName(QString::fromUtf8("label_5"));
        label_5->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_5, 5, 0, 1, 1);

        spinMaxAmp = new QDoubleSpinBox(frame);
        spinMaxAmp->setObjectName(QString::fromUtf8("spinMaxAmp"));
        spinMaxAmp->setMinimum(-99.989999999999995);
        spinMaxAmp->setValue(-5.000000000000000);

        gridLayout->addWidget(spinMaxAmp, 5, 1, 1, 1);

        label_6 = new QLabel(frame);
        label_6->setObjectName(QString::fromUtf8("label_6"));
        label_6->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_6, 8, 0, 1, 1);

        spinTimeWindow = new QDoubleSpinBox(frame);
        spinTimeWindow->setObjectName(QString::fromUtf8("spinTimeWindow"));
        spinTimeWindow->setMinimum(0.100000000000000);
        spinTimeWindow->setMaximum(600.000000000000000);
        spinTimeWindow->setValue(20.000000000000000);

        gridLayout->addWidget(spinTimeWindow, 8, 1, 1, 1);

        label_7 = new QLabel(frame);
        label_7->setObjectName(QString::fromUtf8("label_7"));
        label_7->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_7, 9, 0, 1, 1);

        spinOverlap = new QDoubleSpinBox(frame);
        spinOverlap->setObjectName(QString::fromUtf8("spinOverlap"));
        spinOverlap->setMinimum(0.000000000000000);
        spinOverlap->setMaximum(99.000000000000000);
        spinOverlap->setValue(50.000000000000000);

        gridLayout->addWidget(spinOverlap, 9, 1, 1, 1);

        label_8 = new QLabel(frame);
        label_8->setObjectName(QString::fromUtf8("label_8"));
        label_8->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_8, 3, 0, 1, 1);

        cbShowAxis = new QCheckBox(frame);
        cbShowAxis->setObjectName(QString::fromUtf8("cbShowAxis"));

        gridLayout->addWidget(cbShowAxis, 3, 1, 1, 1);

        label_10 = new QLabel(frame);
        label_10->setObjectName(QString::fromUtf8("label_10"));
        label_10->setAlignment(Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter);

        gridLayout->addWidget(label_10, 7, 0, 1, 1);

        spinMinFrequency = new QDoubleSpinBox(frame);
        spinMinFrequency->setObjectName(QString::fromUtf8("spinMinFrequency"));
        spinMinFrequency->setMaximum(10000.000000000000000);

        gridLayout->addWidget(spinMinFrequency, 6, 1, 1, 1);

        spinMaxFrequency = new QDoubleSpinBox(frame);
        spinMaxFrequency->setObjectName(QString::fromUtf8("spinMaxFrequency"));
        spinMaxFrequency->setMaximum(10000.000000000000000);

        gridLayout->addWidget(spinMaxFrequency, 7, 1, 1, 1);

        cbNormalization = new QComboBox(frame);
        cbNormalization->addItem(QString());
        cbNormalization->addItem(QString());
        cbNormalization->addItem(QString());
        cbNormalization->setObjectName(QString::fromUtf8("cbNormalization"));

        gridLayout->addWidget(cbNormalization, 2, 1, 1, 1);


        verticalLayout->addWidget(frame);

        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        horizontalSpacer = new QSpacerItem(558, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout->addItem(horizontalSpacer);

        btnApply = new QPushButton(SpectrogramSettings);
        btnApply->setObjectName(QString::fromUtf8("btnApply"));

        horizontalLayout->addWidget(btnApply);


        verticalLayout->addLayout(horizontalLayout);

        verticalSpacer = new QSpacerItem(20, 0, QSizePolicy::Minimum, QSizePolicy::Expanding);

        verticalLayout->addItem(verticalSpacer);


        retranslateUi(SpectrogramSettings);

        QMetaObject::connectSlotsByName(SpectrogramSettings);
    } // setupUi

    void retranslateUi(QWidget *SpectrogramSettings)
    {
        SpectrogramSettings->setWindowTitle(QCoreApplication::translate("SpectrogramSettings", "Spectrogram Settings", nullptr));
        label_9->setText(QCoreApplication::translate("SpectrogramSettings", "Min. frequency:", nullptr));
        label->setText(QCoreApplication::translate("SpectrogramSettings", "Smoothing:", nullptr));
        cbSmoothing->setText(QString());
        label_2->setText(QCoreApplication::translate("SpectrogramSettings", "Log scale:", nullptr));
        cbLogScale->setText(QString());
        label_3->setText(QCoreApplication::translate("SpectrogramSettings", "Normalization:", nullptr));
        label_4->setText(QCoreApplication::translate("SpectrogramSettings", "Min. amplitude:", nullptr));
        spinMinAmp->setSuffix(QCoreApplication::translate("SpectrogramSettings", " log10(amp^2)", nullptr));
        label_5->setText(QCoreApplication::translate("SpectrogramSettings", "Max. amplitude:", nullptr));
        spinMaxAmp->setSuffix(QCoreApplication::translate("SpectrogramSettings", " log10(amp^2)", nullptr));
        label_6->setText(QCoreApplication::translate("SpectrogramSettings", "Time window:", nullptr));
        spinTimeWindow->setSuffix(QCoreApplication::translate("SpectrogramSettings", "s", nullptr));
        label_7->setText(QCoreApplication::translate("SpectrogramSettings", "Overlap:", nullptr));
        spinOverlap->setSuffix(QCoreApplication::translate("SpectrogramSettings", "%", nullptr));
        label_8->setText(QCoreApplication::translate("SpectrogramSettings", "Show axis:", nullptr));
        cbShowAxis->setText(QString());
        label_10->setText(QCoreApplication::translate("SpectrogramSettings", "Max. frequency:", nullptr));
        spinMinFrequency->setSpecialValueText(QString());
        spinMinFrequency->setSuffix(QCoreApplication::translate("SpectrogramSettings", " Hz", nullptr));
        spinMaxFrequency->setSpecialValueText(QCoreApplication::translate("SpectrogramSettings", "Auto", nullptr));
        spinMaxFrequency->setSuffix(QCoreApplication::translate("SpectrogramSettings", " Hz", nullptr));
        cbNormalization->setItemText(0, QCoreApplication::translate("SpectrogramSettings", "Fixed", nullptr));
        cbNormalization->setItemText(1, QCoreApplication::translate("SpectrogramSettings", "Frequency", nullptr));
        cbNormalization->setItemText(2, QCoreApplication::translate("SpectrogramSettings", "Time", nullptr));

        btnApply->setText(QCoreApplication::translate("SpectrogramSettings", "Apply", nullptr));
    } // retranslateUi

};

namespace Ui {
    class SpectrogramSettings: public Ui_SpectrogramSettings {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_SPECTROGRAMSETTINGS_H
