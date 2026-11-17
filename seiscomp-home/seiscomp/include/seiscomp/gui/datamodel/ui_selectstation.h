/********************************************************************************
** Form generated from reading UI file 'selectstation.ui'
**
** Created by: Qt User Interface Compiler version 5.15.13
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_SELECTSTATION_H
#define UI_SELECTSTATION_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QDialog>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QTableView>
#include <QtWidgets/QVBoxLayout>

QT_BEGIN_NAMESPACE

class Ui_SelectStation
{
public:
    QVBoxLayout *verticalLayout;
    QGridLayout *gridLayout;
    QLabel *labelNSLC;
    QLineEdit *lineEditNSLC;
    QCheckBox *cbExcludeNSLC;
    QLabel *label;
    QComboBox *comboNetworkType;
    QCheckBox *cbExcludeNetworkType;
    QLabel *label_2;
    QComboBox *comboStationType;
    QCheckBox *cbExcludeStationType;
    QLabel *label_3;
    QComboBox *comboSensorUnit;
    QCheckBox *cbExcludeSensorUnit;
    QTableView *table;
    QHBoxLayout *hboxLayout;
    QSpacerItem *spacerItem;
    QPushButton *btnAdd;

    void setupUi(QDialog *SelectStation)
    {
        if (SelectStation->objectName().isEmpty())
            SelectStation->setObjectName(QString::fromUtf8("SelectStation"));
        SelectStation->resize(854, 788);
        verticalLayout = new QVBoxLayout(SelectStation);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        gridLayout = new QGridLayout();
        gridLayout->setObjectName(QString::fromUtf8("gridLayout"));
        labelNSLC = new QLabel(SelectStation);
        labelNSLC->setObjectName(QString::fromUtf8("labelNSLC"));

        gridLayout->addWidget(labelNSLC, 0, 0, 1, 1);

        lineEditNSLC = new QLineEdit(SelectStation);
        lineEditNSLC->setObjectName(QString::fromUtf8("lineEditNSLC"));

        gridLayout->addWidget(lineEditNSLC, 0, 1, 1, 1);

        cbExcludeNSLC = new QCheckBox(SelectStation);
        cbExcludeNSLC->setObjectName(QString::fromUtf8("cbExcludeNSLC"));

        gridLayout->addWidget(cbExcludeNSLC, 0, 2, 1, 1);

        label = new QLabel(SelectStation);
        label->setObjectName(QString::fromUtf8("label"));

        gridLayout->addWidget(label, 1, 0, 1, 1);

        comboNetworkType = new QComboBox(SelectStation);
        comboNetworkType->addItem(QString());
        comboNetworkType->setObjectName(QString::fromUtf8("comboNetworkType"));

        gridLayout->addWidget(comboNetworkType, 1, 1, 1, 1);

        cbExcludeNetworkType = new QCheckBox(SelectStation);
        cbExcludeNetworkType->setObjectName(QString::fromUtf8("cbExcludeNetworkType"));

        gridLayout->addWidget(cbExcludeNetworkType, 1, 2, 1, 1);

        label_2 = new QLabel(SelectStation);
        label_2->setObjectName(QString::fromUtf8("label_2"));

        gridLayout->addWidget(label_2, 2, 0, 1, 1);

        comboStationType = new QComboBox(SelectStation);
        comboStationType->addItem(QString());
        comboStationType->setObjectName(QString::fromUtf8("comboStationType"));

        gridLayout->addWidget(comboStationType, 2, 1, 1, 1);

        cbExcludeStationType = new QCheckBox(SelectStation);
        cbExcludeStationType->setObjectName(QString::fromUtf8("cbExcludeStationType"));

        gridLayout->addWidget(cbExcludeStationType, 2, 2, 1, 1);

        label_3 = new QLabel(SelectStation);
        label_3->setObjectName(QString::fromUtf8("label_3"));

        gridLayout->addWidget(label_3, 3, 0, 1, 1);

        comboSensorUnit = new QComboBox(SelectStation);
        comboSensorUnit->addItem(QString());
        comboSensorUnit->setObjectName(QString::fromUtf8("comboSensorUnit"));

        gridLayout->addWidget(comboSensorUnit, 3, 1, 1, 1);

        cbExcludeSensorUnit = new QCheckBox(SelectStation);
        cbExcludeSensorUnit->setObjectName(QString::fromUtf8("cbExcludeSensorUnit"));

        gridLayout->addWidget(cbExcludeSensorUnit, 3, 2, 1, 1);


        verticalLayout->addLayout(gridLayout);

        table = new QTableView(SelectStation);
        table->setObjectName(QString::fromUtf8("table"));
        table->setAlternatingRowColors(true);
        table->setSelectionBehavior(QAbstractItemView::SelectRows);

        verticalLayout->addWidget(table);

        hboxLayout = new QHBoxLayout();
        hboxLayout->setSpacing(6);
        hboxLayout->setObjectName(QString::fromUtf8("hboxLayout"));
        hboxLayout->setContentsMargins(0, 0, 0, 0);
        spacerItem = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        hboxLayout->addItem(spacerItem);

        btnAdd = new QPushButton(SelectStation);
        btnAdd->setObjectName(QString::fromUtf8("btnAdd"));

        hboxLayout->addWidget(btnAdd);


        verticalLayout->addLayout(hboxLayout);

        QWidget::setTabOrder(lineEditNSLC, cbExcludeNSLC);
        QWidget::setTabOrder(cbExcludeNSLC, comboNetworkType);
        QWidget::setTabOrder(comboNetworkType, cbExcludeNetworkType);
        QWidget::setTabOrder(cbExcludeNetworkType, comboStationType);
        QWidget::setTabOrder(comboStationType, cbExcludeStationType);
        QWidget::setTabOrder(cbExcludeStationType, comboSensorUnit);
        QWidget::setTabOrder(comboSensorUnit, cbExcludeSensorUnit);
        QWidget::setTabOrder(cbExcludeSensorUnit, table);
        QWidget::setTabOrder(table, btnAdd);

        retranslateUi(SelectStation);
        QObject::connect(btnAdd, SIGNAL(clicked()), SelectStation, SLOT(accept()));

        QMetaObject::connectSlotsByName(SelectStation);
    } // setupUi

    void retranslateUi(QDialog *SelectStation)
    {
        SelectStation->setWindowTitle(QCoreApplication::translate("SelectStation", "Add station(s)", nullptr));
        labelNSLC->setText(QCoreApplication::translate("SelectStation", "NET.STA:", nullptr));
        cbExcludeNSLC->setText(QCoreApplication::translate("SelectStation", "Exclude", nullptr));
        label->setText(QCoreApplication::translate("SelectStation", "Network type:", nullptr));
        comboNetworkType->setItemText(0, QCoreApplication::translate("SelectStation", "- No filter -", nullptr));

        cbExcludeNetworkType->setText(QCoreApplication::translate("SelectStation", "Exclude", nullptr));
        label_2->setText(QCoreApplication::translate("SelectStation", "Station type:", nullptr));
        comboStationType->setItemText(0, QCoreApplication::translate("SelectStation", "- No filter -", nullptr));

        cbExcludeStationType->setText(QCoreApplication::translate("SelectStation", "Exclude", nullptr));
        label_3->setText(QCoreApplication::translate("SelectStation", "Sensor unit:", nullptr));
        comboSensorUnit->setItemText(0, QCoreApplication::translate("SelectStation", "- No filter- ", nullptr));

        cbExcludeSensorUnit->setText(QCoreApplication::translate("SelectStation", "Exclude", nullptr));
        btnAdd->setText(QCoreApplication::translate("SelectStation", "Add", nullptr));
    } // retranslateUi

};

namespace Ui {
    class SelectStation: public Ui_SelectStation {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_SELECTSTATION_H
